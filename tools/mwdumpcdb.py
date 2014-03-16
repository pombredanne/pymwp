#!/usr/bin/env python
#
# Usage examples:
#  $ mwdumpcdb.py -Z jawiki.txt.cdb 19 23 346 9287
#  $ mwdumpcdb.py -Z -w jawiki.wiki.cdb
#  $ mwdumpcdb.py -Z -o all.txt.gz jawiki.txt.cdb
#
import sys
import os.path
from pymwp.utils import getfp
from pymwp.mwcdb import WikiDBReader

# main
def main(argv):
    import getopt
    def usage():
        print ('usage: %s {-w} [-c codec] [-o output] [-T] [-Z] '
               'cdbfile [pageid ...]' % argv[0])
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'wo:c:TZ')
    except getopt.GetoptError:
        return usage()
    text = True
    output = '-'
    codec = 'utf-8'
    ext = ''
    titleline = False
    for (k, v) in opts:
        if k == '-o': output = v
        elif k == '-c': codec = v
        elif k == '-w': text = False
        elif k == '-T': titleline = True
        elif k == '-Z': ext = '.gz'
    if not args: return usage()
    (_,outfp) = getfp(output, 'w')
    readers = []
    pageids = []
    for arg in args:
        if os.path.isfile(arg):
            readers.append(WikiDBReader(arg, codec=codec, ext=ext))
        else:
            pageids.append(arg)
    for reader in readers:
        for pageid in (pageids or iter(reader)):
            try:
                (title, revids) = reader[pageid]
            except KeyError:
                continue
            if titleline:
                outfp.write(title.encode(codec, 'ignore')+'\n')
            for revid in revids:
                try:
                    if text:
                        data = reader.get_text(pageid, revid)
                    else:
                        data = reader.get_wiki(pageid, revid)
                except KeyError:
                    continue
                outfp.write(data.encode(codec, 'ignore'))
    return

if __name__ == '__main__': sys.exit(main(sys.argv))
