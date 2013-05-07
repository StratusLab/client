<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:slterms="http://mp.stratuslab.eu/slterms#"
    xmlns:slreq="http://mp.stratuslab.eu/slreq#"
    xml:base="http://mp.stratuslab.eu/">

    <rdf:Description rdf:about="#%(identifier)s">

        <dcterms:identifier>%(identifier)s</dcterms:identifier>

        <slreq:bytes>%(bytes)s</slreq:bytes>

        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>MD5</slreq:algorithm>
            <slreq:value>%(md5)s</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-1</slreq:algorithm>
            <slreq:value>%(sha1)s</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-256</slreq:algorithm>
            <slreq:value>%(sha256)s</slreq:value>
        </slreq:checksum>
        <slreq:checksum rdf:parseType="Resource">
            <slreq:algorithm>SHA-512</slreq:algorithm>
            <slreq:value>%(sha512)s</slreq:value>
        </slreq:checksum>

        <slreq:endorsement rdf:parseType="Resource"/>

        <dcterms:type>%(type)s</dcterms:type>
        <slterms:kind>%(kind)s</slterms:kind>

        <slterms:os>%(os)s</slterms:os>
        <slterms:os-version>%(osversion)s</slterms:os-version>
        <slterms:os-arch>%(arch)s</slterms:os-arch>
        <slterms:version>%(version)s</slterms:version>
        <dcterms:compression>%(compression)s</dcterms:compression>
        %(_locations_xml)s

        <dcterms:format>%(format)s</dcterms:format>

        <dcterms:creator>%(creator)s</dcterms:creator>

        <dcterms:created>%(created)s</dcterms:created>
        <dcterms:valid>%(valid)s</dcterms:valid>

        <dcterms:title>%(title)s</dcterms:title>
        <dcterms:alternative>%(tag)s</dcterms:alternative>
        <dcterms:description>%(comment)s</dcterms:description>

        <slterms:hypervisor>%(hypervisor)s</slterms:hypervisor>
        <slterms:disks-bus>%(disksbus)s</slterms:disks-bus>

        <dcterms:publisher>%(publisher)s</dcterms:publisher>
        %(deprecated)s

    </rdf:Description>
</rdf:RDF>
