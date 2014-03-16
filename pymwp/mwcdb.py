#!/usr/bin/env python
import sys
from pycdb import CDBReader
from pycdb import CDBMaker
from utils import compress, decompress, getfp


##  WikiDBReader
##
class WikiDBReader(object):

    def __init__(self, path, ext='', codec='utf-8'):
        self._reader = CDBReader(path)
        self.ext = ext
        self.codec = codec
        return

    def __iter__(self):
        return self.get_pageids()

    def __getitem__(self, pageid):
        return self.get_page(pageid)

    def _get_data(self, key):
        data = self._reader[key]
        data = decompress(key, data)
        return data.decode(self.codec, 'ignore')

    def get_pageids(self):
        for key in self._reader.iterkeys():
            if key.endswith(':title'):
                (pageid,_,_) = key.partition(':')
                yield int(pageid)
        return

    def get_page(self, pageid):
        key = ('%s:title' % pageid)
        title = self._reader[key].decode(self.codec, 'ignore')
        key = ('%s:revs' % pageid)
        revids = self._reader[key].split(' ')
        return (title, revids)

    def get_wiki(self, pageid, revid):
        key = '%s/%s:wiki' % (pageid, revid)
        key += self.ext
        return self._get_data(key)

    def get_text(self, pageid, revid):
        key = '%s/%s:text' % (pageid, revid)
        key += self.ext
        return self._get_data(key)


##  WikiDBWriter
##
class WikiDBWriter(object):

    def __init__(self, pathpat, ext='', codec='utf-8', maxsize=2**31):
        self.pathpat = pathpat
        self.ext = ext
        self.codec = codec
        self.maxsize = maxsize
        self._index = 0
        self._maker = None
        self._pageid = None
        self._revids = []
        return

    def _new_page(self, pageid):
        if self._pageid != pageid:
            if self._revids:
                revs = ' '.join( str(revid) for revid in self._revids )
                self._maker.add('%s:revs' % self._pageid, revs)
            self._revids = []
            self._pageid = pageid
        if self._maker is not None:
            if self._pageid is None or self.maxsize <= self._maker.get_size():
                self._maker.finish()
                self._maker = None
        if self._maker is None:
            if self._pageid is not None:
                path = (self.pathpat % {'index':self._index})
                self._maker = CDBMaker(path)
                self._index += 1
        return

    def _add_data(self, key, value):
        data = value.encode(self.codec, 'ignore')
        data = compress(key, data)
        self._maker.add(key, data)
        return

    def close(self):
        self._new_page(None)
        return

    def add_page(self, pageid, title):
        self._new_page(pageid)
        title = title.encode(self.codec, 'ignore')
        self._maker.add('%s:title' % pageid, title)
        return

    def add_revid(self, pageid, revid):
        assert self._pageid == pageid
        self._revids.append(revid)
        return

    def add_wiki(self, pageid, revid, wiki):
        assert revid in self._revids
        key = '%s/%s:wiki' % (pageid, revid)
        key += self.ext
        self._add_data(key, wiki)
        return

    def add_text(self, pageid, revid, wiki):
        assert revid in self._revids
        key = '%s/%s:text' % (pageid, revid)
        key += self.ext
        self._add_data(key, wiki)
        return


##  WikiFileWriter
##
class WikiFileWriter(object):

    def __init__(self, output=None, pathpat=None,
                 codec='utf-8', titleline=False):
        assert output is not None or pathpat is not None
        self.pathpat = pathpat
        self.codec = codec
        self.titleline = titleline
        self._fp = None
        if output is not None:
            (_,self._fp) = getfp(output, mode='w')
        self._pageid = None
        self._title = None
        self._revid = None
        return
        
    def close(self):
        if self._fp is not None:
            self._fp.close()
        return

    def add_page(self, pageid, title):
        self._pageid = pageid
        self._title = title
        return
        
    def add_revid(self, pageid, revid):
        assert self._pageid == pageid
        self._revid = revid
        return
    
    def add_data(self, pageid, revid, data):
        assert self._pageid == pageid
        assert self._title is not None
        assert self._revid == revid
        if self.pathpat is not None:
            if self._fp is not None:
                self._fp.close()
            name = self._title.encode('utf-8').encode('quopri_codec')
            path = (self.pathpat % {'name':name, 'pageid':pageid})
            (_,self._fp) = getfp(path, 'w')
        assert self._fp is not None
        if self.titleline:
            title = self._title.encode(self.codec, 'ignore')
            self._fp.write(title+'\n')
        self._fp.write(data.encode(self.codec, 'ignore'))
        self._fp.write('\n\f')
        return

    add_wiki = add_data
    add_text = add_data


# main
def main(argv):
    args = argv[1:]
    for path in args:
        reader = WikiDBReader(path)
        for (pageid,title) in reader:
            print (pageid, title)
            (_,revids) = reader[pageid]
            for revid in revids:
                wiki = reader.get_wiki(pageid, revid)
                print wiki.encode('utf-8')
            print
    return

if __name__ == '__main__': sys.exit(main(sys.argv))
