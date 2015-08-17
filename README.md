#Nice Python client for Pipedrive

Small, but efficient Python client for the [Pipedrive API](http://developers.pipedrive.com). Started because no client properly support custom fields in a nice way. Inspired by the [pipedrive cient for node.js](https://github.com/pipedrive/client-nodejs) and my needs.

###Main features
- support pipedrive object model (and easy to implement more)
- read/write any resource you can fetch
- advanced support for custom fields, easy access using a convenient name instead of pipedrive random key
- easy access to properties: `object.fieldname` including custom fields
- and to list of subobjects: `person.deals()`, `deal.files()`, etc.
- easy list / search on any resource `pd.list_all(Person)`, `pd.query(Person, args`


###TODO
- create/delete resource (only supports get/update for now)
- proper python module layout
- convert ipython notebook for tests to unit tests

Pull requests welcome!

##Install

Nothing special for now, place this repository in your python project and `import pypedrive`. Pip package coming some days.

##Usage

You can try this in a ipython notebook.

```python
#Some setup
> from config import *
> import pipedrive
> pd = pipedrive.PipedriveClient(PD_API_TOKEN) #pipedrive client, shared


#Fetch a person
> person = pipedrive.Person(pd, 3000)
> print(person.id)
3000
> print(person.leadscore) #Hello custom field!
12

#Play with a deal
> deal = pipedrive.Deal(pd, 119)
> print (deal.id)
118
> print (deal.title)
My Customer Project
> print (deal.value)
520000
> print (int(deal.age['total_seconds']/3600/24))
98

#And an organization
> org = pipedrive.Organization(pd, 127)
> print (org.name)
Liferay

> r = pd.search(pipedrive.Deal, term="nuxeo")
> for d in r: print (d.org_id.name)
Client A
Client B
...
Client X

> r = pd.list_all(pipedrive.Pipeline)
> for d in r: print ("[%s] %s" % (d.id, d.name))
[1] US Subscription (New and Upsell)
[4] US Renewals
[5] US Services

> p = pipedrive.Pipeline(pd, 1)
> for d in p.deals(status="lost"): 
>     print ("Deal %s valued %s" % (d.title, d.value))
Deal A valued 50000
Deal B valued 70000
...
Deal X valued 120000
```



