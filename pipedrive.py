import requests
from .util import *
import json

API_ENDPOINT = "https://api.pipedrive.com/v1"


class PipedriveClient():

    def __init__(self, api_token):
        self.api_token = api_token
        self.endpoint = API_ENDPOINT
        self.fields = {}

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

    def person_search(self, text, email=False):
        pass

    def _fetch_resource(self, resource, rid=None):
        url = self._build_url(resource, rid)
        debug("Fetching resource %s (%s) at %s" % (rid, resource, url))
        r = requests.get(url)
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

        (r, fdata) = self._fetch_resource(resource + "Fields")

        for f in fdata:
            attr = to_snake_case(f["name"])
            key = f["key"]
            key_to_attr[key] = attr
            attr_to_key[attr] = key

        fields["key_to_attr"] = key_to_attr
        fields["attr_to_key"] = attr_to_key
        self.fields[resource] = fields

    def update_resource(self, resource, rid, data):
        url = self._build_url(resource, rid)
        # XXX todo Validate resource/id/data types
        debug("Updating resource %s (%s) at %s" % (rid, resource, url))
        headers = {"Content-Type": "application/json"}
        r = requests.put(url, data=json.dumps(data), headers=headers)
        debug("Update status code: %s" % r.status_code)
        r.raise_for_status()
        return

    def _build_url(self, resource, rid=None):
        url = self.endpoint + "/" + resource
        if rid is not None:
            url = url + "/" + str(rid)
        url = url + "?api_token=%s" % (self.api_token)
        return url


class BaseResource(object):
    RESOURCE = "resources"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = False

    def __init__(self, client, id):
        self._client = client
        self._resource = self.RESOURCE
        self.id = id
        self._data_cache = {}
        self.url = None
        self._fields = None
        self._dirty_fields = set()

        if self._resource not in self._client.fields:
            self._client.load_fields_for_resource(self._resource)
        self._init_done = True

    def __getattr__(self, name):

        attr = self._name_to_attr(name)

        if attr in self._data:
            value = self._data[attr]
            return value
        else:
            raise AttributeError

    def __setattr__(self, name, value):
        #print("Setting %s to %s" % (name, value))
        if "_init_done" not in self.__dict__ or name in self.__dict__:
            # use default setattr
            object.__setattr__(self, name, value)
        elif name in self.field_names:
            # custom field, let's set it
            attr = self._name_to_attr(name)
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
    def field_keys(self):
        if not self.HAS_CUSTOM_FIELDS:
            return []
        return self._client.fields[self._resource]["key_to_attr"]

    @property
    def field_names(self):
        if not self.HAS_CUSTOM_FIELDS:
            return []
        return self._client.fields[self._resource]["attr_to_key"]


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


class Acivity(BaseResource):
    RESOURCE = "activity"
    RESOURCE_SEGMENT = "activities"
    HAS_CUSTOM_FIELDS = False


class Stage(BaseResource):
    RESOURCE = "stage"
    RESOURCE_SEGMENT = RESOURCE + "s"
    HAS_CUSTOM_FIELDS = False
