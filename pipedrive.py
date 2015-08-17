import requests
import json
from .util import *
from .resources import *

API_ENDPOINT = "https://api.pipedrive.com/v1"


class PipedriveResultSet(object):

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

        self.fetch_next_page()

    def __iter__(self):
        return self

    def __next__(self):
        if len(self._results) == 0 and not self.has_more:
            raise StopIteration

        if len(self._results) == 0 and self.has_more:
            self.fetch_next_page()

        return self._results.pop(0)

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

    def _build_url(self, resource, rid=None, command=None):
        url = self.endpoint + "/" + resource
        if rid is not None:
            url += "/" + str(rid)
        if command is not None:
            url += "/" + str(command)

        url = url + "?api_token=%s" % (self.api_token)
        return url
