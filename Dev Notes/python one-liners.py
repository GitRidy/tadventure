# merge a list of tuples into a list
l1 = [(1,2), (3,4), (5,6,7)]
l2 = [e for t in l1 for e in t]
print (l2)