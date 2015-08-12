import requests
from .util import *
import json

API_ENDPOINT = "https://api.pipedrive.com/v1"


class BaseResource(object):
    RESOURCE = "resources"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = False

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

        if self._resource not in self._client.fields:
            self._client.load_fields_for_resource(self._resource)

        if preload is not None:
            self._data_cache = preload

        self._init_done = True

    def __getattr__(self, name):

        attr = self._name_to_attr(name)

        if name in self.field_names and attr not in self._data:
            self._data_cache.clear()

        if attr in self._data:
            value = self._data[attr]
            ftype = self.field_config[attr]["type"]
            if ftype in self._client.FIELD_TO_CLASS:
                # if type is mappable, map it
                resource_class = self._client.FIELD_TO_CLASS[ftype]
                rid = value["value"]
                res = resource_class(self._client, rid)
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

    def save(self):
        "Save data back to pipedrive"

        if not self.active:
            raise Exception("Can't save resource %s: record deleted in Pipedrive" % self.id)

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


class Person(BaseResource):
    RESOURCE = "person"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = True


class Deal(BaseResource):
    RESOURCE = "deal"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = True


class Organization(BaseResource):
    RESOURCE = "organization"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = True


class Product(BaseResource):
    RESOURCE = "product"
    RESOURCE_SEGMENT = RESOURCE + "s"
    HAS_CUSTOM_FIELDS = True
    FIELD_SEGMENT = RESOURCE + "Fields"


class User(BaseResource):
    RESOURCE = "user"
    RESOURCE_SEGMENT = RESOURCE + "s"
    HAS_CUSTOM_FIELDS = False


class Acivity(BaseResource):
    RESOURCE = "activity"
    RESOURCE_SEGMENT = "activities"
    HAS_CUSTOM_FIELDS = False


class Stage(BaseResource):
    RESOURCE = "stage"
    RESOURCE_SEGMENT = RESOURCE + "s"
    HAS_CUSTOM_FIELDS = False


class PipedriveResultSet(object):
    """Generic handle for query and paginable result sets / filter
    set from pipedrive"""

    def __init__(self, client, data, page_size=None):
        self._data = data
        self._client = client
        self._page_size = page_size

    def __iter__(self):
        return self

    def __next__(self):
        pass

    def fetch_next_page(self):
        pass

    def has_more_item(self):
        pass


class PipedriveClient():

    FIELD_TO_CLASS = {
        "people": Person,
        "org": Organization,
        "stage": Stage,
        "product": Product
    }

    def __init__(self, api_token):
        self.api_token = api_token
        self.endpoint = API_ENDPOINT
        self.fields = {}
        self._session = requests.Session()

    def get_contact(self, id):
        res = "persons"
        (r, contact) = self._fetch_resource_by_id(res, id)
        return contact

    def get_resource(self, id):
        res = "persons"
        (r, resource) = self._fetch_resource_by_id(res, id)
        return (r, resource)

    def _fetch_resource_by_id(self, resource, id):

        if id is None:
            raise Exception("Can't fetch, ID given is None.")

        return self._fetch_resource(resource, id)

    def query(self, klass, term, **kw):
        """Perform a search for a pipedrive resource.
        kwargs may be org_id, person_id, email.
        Typically to find a person by it's email address:
        query(Person, term="toto@toto.com", email=True)
        """
        res = klass.RESOURCE_SEGMENT
        url = self._build_url(res, rid=None, command="find")
        print(url)
        params = {"term": term}
        if kw:
            for name, value in kw.iteritems():
                params[name] = value
        r = self._session.get(url, params)
        print(r.json())
        data = r.json()["data"]
        resultset = [klass(self, i["id"], preload=i) for i in data]
        for i in resultset:
            print(i.lead_score)

    def _fetch_resource(self, resource, rid=None):
        url = self._build_url(resource, rid)
        debug("Fetching resource %s (%s) at %s" % (rid, resource, url))
        r = self._session.get(url)
        data = r.json()

        if "success" not in data:
            raise Exception("Bad Response - can't find success key.")

        if not data["success"]:
            msg = data.get("error", "no error message given")
            raise Exception("Pipedrive error - %s at %s" % (msg, r.url))

        if "data" not in data:
            raise Exception("Can't find data object in response: %s" % data)

        return (r, data["data"])

    def load_fields_for_resource(self, resource):

        debug("Loading fields for resource %s" % resource)
        fields = {}
        key_to_attr = {}
        attr_to_key = {}
        field_definition = {}

        (r, fdata) = self._fetch_resource(resource + "Fields")

        for f in fdata:
            key = f["key"]
            if len(key) == 40:
                # custom field, use a nicer name
                attr = to_snake_case(f["name"])
            else:
                # not a custom field, use key name
                attr = key
            key_to_attr[key] = attr
            attr_to_key[attr] = key
            field_definition[key] = {"type": f["field_type"],
                                     "editable": f["edit_flag"]}
            if "options" in f:
                field_definition["options"] = f["options"]

        fields["key_to_attr"] = key_to_attr
        fields["attr_to_key"] = attr_to_key
        fields["config"] = field_definition
        self.fields[resource] = fields

    def update_resource(self, resource, rid, data):
        url = self._build_url(resource, rid)
        # XXX todo Validate resource/id/data types
        debug("Updating resource %s (%s) at %s" % (rid, resource, url))
        headers = {"Content-Type": "application/json"}
        r = self._session.put(url, data=json.dumps(data), headers=headers)
        data = r.json()
        debug("Update status code: %s" % r.status_code)
        r.raise_for_status()
        if "data" in data:
            return data["data"]

    def _build_url(self, resource, rid=None, command=None):
        url = self.endpoint + "/" + resource
        if rid is not None:
            url += "/" + str(rid)
        if command is not None:
            url += "/" + str(command)
        url = url + "?api_token=%s" % (self.api_token)
        return url
