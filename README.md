#Nice Python client for Pipedrive

Small, but efficient Python client for the [Pipedrive API](http://developers.pipedrive.com). Started because no client properly support custom fields in a nice way.

Main features:
- support pipedrive object model (and easy to implement more)
- advanced support for custom fields, easy access using a convenient name instead of pipedrive random key
- natural api to access properties: `object.fieldname` including custom fields

TODO:
- implement more query/search options
- support write
- support more objects

Pull requests welcome!

##Install

Nothing special for now, just use the single file. Pip package coming some days.

##Usage

    #Some setup
    from config import *
    import pipedrive
    pd = pipedrive.PipedriveClient(PD_API_TOKEN) #pipedrive client, shared


    #Fetch a person
    person = pipedrive.Person(pd, 3000)
    print(person.id)
    print(person.leadscore) #Hello custom field!

    >3000
    >12

    #Play with a deal
    deal = pipedrive.Deal(pd, 119)
    print (deal.id)
    print (deal.title)
    print (deal.value)
    print (int(deal.age['total_seconds']/3600/24))

    >118
    >Valeo Services
    >19000
    >98


    #And an organization
    org = pipedrive.Organization(pd, 127)
    print (org.name)

    >Liferay



