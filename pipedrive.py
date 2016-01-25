import requests
import json
from .util import *
from .resources import *

API_ENDPOINT = "https://api.pipedrive.com/v1"


class PipedriveClient():

    FIELD_TO_CLASS = {
        "people": Person,
        "org": Organization,
        "stage": Stage,
        "product": Product,
        "pipeline": Pipeline,
        "participant": Person
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

    def search(self, klass, term, **kw):
        """Perform a search for a pipedrive resource.
        kwargs may be org_id, person_id, email.
        Typically to find a person by it's email address:
        query(Person, term="toto@toto.com", email=True)
        """
        res = klass.RESOURCE_SEGMENT
        url = self._build_url(res, rid=None, command="find")
        params = {"term": term}
        if kw:
            for name, value in kw.items():
                params[name] = value
        req = requests.Request("GET", url, params=params)

        return PipedriveResultSet(klass, self, req)

    def list_all(self, klass, **kw):
        res = klass.RESOURCE_SEGMENT
        url = self._build_url(res, rid=None, command=None)
        params = {}
        if kw:
            for name, value in kw.items():
                params[name] = value
        req = requests.Request("GET", url, params=params)

        return PipedriveResultSet(klass, self, req)

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

    def merge_resource(self, resource, rid, target_id):
        """merge object id into target_id"""
        url = self._build_url(resource, rid, "merge")
        headers = {"Content-Type": "application/json"}
        data = {"id": rid, "merge_with_id": target_id}
        r = self._session.put(url, data=json.dumps(data), headers=headers)
        debug("Merge status code: %s" % r.status_code)
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
