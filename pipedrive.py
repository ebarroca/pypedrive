import requests
from util import *

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

    def fetch_resource_by_id(self, resource, id):

        if id is None:
            raise Exception("Can't fetch, ID given is None.")

        return self._fetch_resource(resource, id)

    def person_search(self, text, email=False):
        pass

    def _fetch_resource(self, resource, rid=None):
        res = resource
        url = self.endpoint + "/" + res
        if rid is not None:
            url = url + "/" + str(rid)
        url = url + "?api_token=%s" % (self.api_token)
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

    def update_score(self, person_id, score):
        res = "/persons"
        url = self.endpoint + res + \
            "/%s?api_token=%s" % (person_id, self.api_token)
        data = {LeadScoreID: score}
        r = requests.put(url, data)
        log(r.status_code)


class BaseResource(object):
    RESOURCE = "resources"
    RESOURCE_SEGMENT = RESOURCE + "s"
    FIELD_SEGMENT = RESOURCE + "Fields"
    HAS_CUSTOM_FIELDS = False

    def __init__(self, client, id):
        self._client = client
        self._resource = self.RESOURCE
        self.id = id
        self._data_cache = None
        self.url = None
        self._fields = None

        if self._resource not in self._client.fields:
            self._client.load_fields_for_resource(self._resource)

    def __getattr__(self, name):

        if self.HAS_CUSTOM_FIELDS and name in self._field_names:
            attr = self._field_names[name]
        else:
            attr = name

        if attr in self._data:
            value = self._data[attr]
            return value
        else:
            raise AttributeError

    @property
    def _data(self):
        if self._data_cache is None:
            (r, data) = self._client.fetch_resource_by_id(
                self.RESOURCE_SEGMENT, self.id)
            self.url = r.url
            self._data_cache = data

        return self._data_cache

    @property
    def _field_keys(self):
        if not self.HAS_CUSTOM_FIELDS:
            return None
        return self._client.fields[self._resource]["key_to_attr"]

    @property
    def _field_names(self):
        if not self.HAS_CUSTOM_FIELDS:
            return None
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
