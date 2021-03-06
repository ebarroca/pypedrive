import requests
from .util import debug

def make_linked_methods(parent, o):
    """
    Generate 'magic' methods to fetch linked objects so that
    org = Organization(pd, 123)
    o.deals() # return an iterable list of deals
    o.files() # return an interable list of files
    """

    segment = o.RESOURCE_SEGMENT

    def linked_objects(**kw):
        # Define dynamic method
        if kw:
            return parent.list_linked_objects(o, **kw)
        else:
            return parent.list_linked_objects(o)

    linked_objects.__name__ = segment
    linked_objects.__doc__ = "Fetch %s linked to this %s" % (
        segment, parent.RESOURCE)

    return linked_objects


class PipedriveResultSet():

    """Generic handle for query and paginable result sets / filter
    set from pipedrive"""

    def __init__(self, klass, client, req):
        self._data_cache = None
        self._results = None
        self._req = req
        self._client = client
        self._klass = klass
        self._results = []
        self._current = 0
        self._next_start = 0
        self._has_more = False

        self.fetch_next_page()

    def __iter__(self):
        return self

    def __next__(self):
        if len(self._results) == 0 and not self.has_more:
            raise StopIteration

        if len(self._results) == 0 and self.has_more:
            self.fetch_next_page()

        return self._results.pop(0)

    #Python 2 compatibility
    next = __next__

    def fetch_next_page(self):
        debug("fetching next page: start: %s, url: %s" % (self._next_start,
                                                          self._req.url))
        self._req.params["start"] = self._next_start

        r = self._client._session.send(self._req.prepare())
        r.raise_for_status()
        self.handle_data(r.json())

    def handle_data(self, data):

        if not data["success"]:
            raise Exception("Issue fetching data at %s: %s" %
                            (self._req.url, data))

        if data["data"] is None:
            debug("No data available: %s" % data)
            return

        self._data_cache = data["data"]
        self._has_more = data["additional_data"][
            "pagination"]["more_items_in_collection"]

        if self.has_more:
            self._next_start = data["additional_data"][
                "pagination"]["next_start"]

        l = [self._klass(self._client, i["id"], preload=i) for i
             in self._data_cache]

        self._results.extend(l)

    @property
    def has_more(self):
        return self._has_more


class SimpleResource(object):
    """
    Base resource class, for resources without custom fields.
    Support basic operations for resources: get, save
    """
    HAS_CUSTOM_FIELDS = False
    LINKED_OBJECTS = None

    def __init__(self, client, id, preload=None):
        """
        client: pipedrive client instance
        id: pipedrive resource id
        preload: set of fields to load at __init__ //TODO: use parameter
        """
        self._client = client
        self._resource = self.RESOURCE
        self.id = id
        self._data_cache = {}
        self.url = None
        self._fields = None
        self._dirty_fields = set()

        # Load fields configuration if resource has custom fields
        if self.HAS_CUSTOM_FIELDS and \
                self._resource not in self._client.fields:
            self._client.load_fields_for_resource(self._resource)

        # Generate methods to fetch linekd objects
        if self.LINKED_OBJECTS is not None:
            for o in self.LINKED_OBJECTS:
                m = make_linked_methods(self, o)
                setattr(self, o.RESOURCE_SEGMENT, m)

        if preload is not None:
            self._data_cache = preload

        self._init_done = True

    def __getattr__(self, name):

        attr = name

        if attr not in self._data:
            self._data_cache.clear()

        if attr in self._data:
            return self._data[attr]
        else:
            raise AttributeError("Can't get property: %s not found" % name)

    def __setattr__(self, name, value):
        if "_init_done" not in self.__dict__ or name in self.__dict__:
            # use default setattr
            object.__setattr__(self, name, value)
        elif name in self._data_cache:
            name = attr
            if not str(self._data[attr]) == str(value):
                self._data_cache[attr] = value
                self._dirty_fields.add(name)
        else:
            raise AttributeError("Can't set propery: attribute %s \
                                          not found." % (name))

    def __str__(self):
        return str(self.id)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and self.id == other.id)

    def __ne__(self, other):
        return not self.__eq__(other)

    def list_linked_objects(self, klass, **kw):
        command = klass.RESOURCE_SEGMENT
        url = self._client._build_url(self.RESOURCE_SEGMENT, rid=self.id,
                                      command=command)
        params = {}
        if kw:
            for name, value in kw.items():
                params[name] = value

        req = requests.Request("GET", url, params=params)

        return PipedriveResultSet(klass, self._client, req)

    def save(self):
        "Save data back to pipedrive"

        if not self.active:
            raise Exception(
                "Can't save resource %s: record deleted in Pipedrive" % self.id)

        if not self._dirty_fields:
            debug("No dirty fields for object %s" % self.id)
            return
        debug("Saving dirty fields: %s" % self._dirty_fields)
        data_for_update = {}
        for f in self._dirty_fields:
            attr = self._name_to_attr(f)
            data_for_update[attr] = self._data[attr]
        self._client.update_resource(self.RESOURCE_SEGMENT, self.id,
                                     data_for_update)
        self._dirty_fields.clear()
        self._data.clear()

    def merge(self, target_id):
        """merge this object with target"""
        if not self.SUPPORT_MERGE:
            raise Exception("Object doesn't support merge")





    @property
    def _data(self):
        if not self._data_cache:
            (r, data) = self._client._fetch_resource_by_id(
                self.RESOURCE_SEGMENT, self.id)
            self.url = r.url
            self._data_cache = data

        return self._data_cache

    @property
    def active(self):
        return self._data["active_flag"]


class CustomResource(SimpleResource):
    """
    Base class for resources with custom fields.
    Handle the custom fields logic, in addition to SimpleResource features.
    Enable to access custom fields with a natural name instead of 40 char hash.
    """

    RESOURCE = "resources"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = True

    def __getattr__(self, name):

        attr = self._name_to_attr(name)

        if name in self.field_names and attr not in self._data:
            self._data_cache.clear()

        if attr in self._data:
            value = self._data[attr]
            ftype = self.field_config[attr]["type"]
            if ftype in self._client.FIELD_TO_CLASS and value is not None:
                # if type is mappable, map it
                resource_class = self._client.FIELD_TO_CLASS[ftype]
                if type(value) == int:
                    rid = value
                    res = resource_class(self._client, rid)
                elif type(value) == dict:
                    rid = value["value"]
                    res = resource_class(self._client, rid, preload=value)
                return res
            else:
                return value
        else:
            raise AttributeError("Can't get property: %s not found" % name)

    def __setattr__(self, name, value):
        if "_init_done" not in self.__dict__ or name in self.__dict__:
            # use default setattr
            object.__setattr__(self, name, value)
        elif name in self.field_names:
            # custom field, let's set it
            attr = self._name_to_attr(name)
            # Set value only if value has actually changed
            if not str(self._data[attr]) == str(value):
                self._data_cache[attr] = value
                self._dirty_fields.add(name)
        else:
            raise AttributeError("Can't set propery: attribute %s \
                                          not found." % (name))

    def _name_to_attr(self, name):
        "Convert property name in pipedrive's object internal key."
        if self.HAS_CUSTOM_FIELDS and name in self.field_names:
            attr = self.field_names[name]
        else:
            attr = name
        return attr
        # Check if test on HAS_CUSTOM_FIELDS is required

    @property
    def field_keys(self):
        if not self.HAS_CUSTOM_FIELDS:
            return []
        return self._client.fields[self._resource]["key_to_attr"]

    @property
    def field_names(self):
        if not self.HAS_CUSTOM_FIELDS:
            return []
        return self._client.fields[self._resource]["attr_to_key"]

    @property
    def field_config(self):
        if not self.HAS_CUSTOM_FIELDS:
            return []
        return self._client.fields[self._resource]["config"]


class User(SimpleResource):
    RESOURCE = "user"
    RESOURCE_SEGMENT = RESOURCE + "s"
    HAS_CUSTOM_FIELDS = False


class Activity(SimpleResource):
    RESOURCE = "activity"
    RESOURCE_SEGMENT = "activities"
    HAS_CUSTOM_FIELDS = False


class EmailMessage(SimpleResource):
    RESOURCE = "emailMessage"
    RESOURCE_SEGMENT = "emailMessages"
    HAS_CUSTOM_FIELDS = False


class EmailThread(SimpleResource):
    RESOURCE = "emailThread"
    RESOURCE_SEGMENT = "emailThreads"
    HAS_CUSTOM_FIELDS = False


class File(SimpleResource):
    RESOURCE = "file"
    RESOURCE_SEGMENT = "files"
    HAS_CUSTOM_FIELDS = False


class Filter(SimpleResource):
    RESOURCE = "filter"
    RESOURCE_SEGMENT = "filters"
    HAS_CUSTOM_FIELDS = False


class Note(SimpleResource):
    RESOURCE = "note"
    RESOURCE_SEGMENT = "notes"
    HAS_CUSTOM_FIELDS = False


class Goal(SimpleResource):
    RESOURCE = "goal"
    RESOURCE_SEGMENT = "goals"
    HAS_CUSTOM_FIELDS = False


class Product(CustomResource):
    RESOURCE = "product"
    RESOURCE_SEGMENT = RESOURCE + "s"
    HAS_CUSTOM_FIELDS = True
    FIELD_SEGMENT = RESOURCE + "Fields"
    LINKED_OBJECTS = [File]


class Deal(CustomResource):
    RESOURCE = "deal"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = True
    LINKED_OBJECTS = [Product, File]


class Stage(SimpleResource):
    RESOURCE = "stage"
    RESOURCE_SEGMENT = RESOURCE + "s"
    HAS_CUSTOM_FIELDS = False
    LINKED_OBJECTS = [Deal]


class Person(CustomResource):
    RESOURCE = "person"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = True
    LINKED_OBJECTS = [Deal, Activity, File, Product]


class Pipeline(SimpleResource):
    RESOURCE = "pipeline"
    RESOURCE_SEGMENT = RESOURCE + "s"
    HAS_CUSTOM_FIELDS = False
    LINKED_OBJECTS = [Deal]


class Organization(CustomResource):
    RESOURCE = "organization"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = True
    LINKED_OBJECTS = [File, Activity, Deal, Person]
