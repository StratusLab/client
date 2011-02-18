import stratuslab.Policy as Policy 
from xml.etree.ElementTree import ElementTree


if __name__ == "__main__":
    metadata = ["valid-full.xml", "hackers-full.xml"]
    
    xmltree = ElementTree()
    xmltree2 = ElementTree()
    xmltree.parse("valid-full.xml")
    xmltree2.parse("hackers-full.xml")
    
    xmltrees = [xmltree, xmltree2]
    
    print 'len(xmltrees)=',len(xmltrees)
    Policy.filter(xmltrees)
    print 'len(xmltrees)=',len(xmltrees)
    Policy.init('policy.cfg')
    print Policy.WhiteListEndorsers
