#!/usr/bin/env python2
#
# usage:
#  $ mwwiki2txt.py -n10 -t 'article%(pageid)05d.txt' jawiki.xml.bz2
#
import re
import sys
from gzip import GzipFile
from bz2 import BZ2File
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from pymwp.mwtokenizer import WikiToken, XMLTagToken, XMLEmptyTagToken
from pymwp.mwparser import WikiTextParser
from pymwp.mwparser import WikiTree, WikiXMLTree, WikiArgTree
from pymwp.mwparser import WikiSpecialTree, WikiCommentTree
from pymwp.mwparser import WikiKeywordTree, WikiLinkTree
from pymwp.mwparser import WikiDivTree
from pymwp.mwparser import WikiTableTree, WikiTableCellTree
from pymwp.mwxmldump import MWXMLDumpFilter
from pymwp.pycdb import CDBReader, CDBMaker


SPC = re.compile(r'\s+')
def rmsp(s): return SPC.sub(' ', s)

IGNORED = re.compile(u'^([-a-z]+|Category|Special):')
def isignored(name): return IGNORED.match(name)


##  WikiTextExtractor
##
class WikiTextExtractor(WikiTextParser):

    def __init__(self, errfp=sys.stderr, codec='utf-8'):
        WikiTextParser.__init__(self)
        self.errfp = errfp
        self.codec = codec
        return

    def error(self, s):
        self.errfp.write(s)
        return

    def invalid_token(self, pos, token):
        if self.errfp is not None:
            self.error('invalid token(%d): %r\n' % (pos, token))
        return

    def convert(self, fp, tree=None):
        if tree is None:
            self.convert(fp, self.get_root())
        elif tree is WikiToken.PAR:
            fp.write('\n')
        elif isinstance(tree, XMLEmptyTagToken):
            if tree.name in XMLTagToken.BR_TAG:
                fp.write('\n')
        elif isinstance(tree, unicode):
            fp.write(rmsp(tree).encode(self.codec, 'ignore'))
        elif isinstance(tree, WikiSpecialTree):
            pass
        elif isinstance(tree, WikiCommentTree):
            pass
        elif isinstance(tree, WikiXMLTree):
            if tree.xml.name in XMLTagToken.NO_TEXT:
                pass
            else:
                for c in tree:
                    self.convert(fp, c)
                if tree.xml.name in XMLTagToken.PAR_TAG:
                    fp.write('\n')
        elif isinstance(tree, WikiKeywordTree):
            if tree:
                if isinstance(tree[0], WikiTree):
                    name = tree[0].get_text()
                else:
                    name = tree[0]
                if isinstance(name, unicode) and not isignored(name):
                    self.convert(fp, tree[-1])
        elif isinstance(tree, WikiLinkTree):
            if 2 <= len(tree):
                for c in tree[1:]:
                    self.convert(fp, c)
                    fp.write(' ')
            elif tree:
                self.convert(fp, tree[0])
        elif isinstance(tree, WikiTableCellTree):
            if tree:
                self.convert(fp, tree[-1])
                fp.write('\n')
        elif isinstance(tree, WikiTableTree):
            for c in tree:
                if not isinstance(c, WikiArgTree):
                    self.convert(fp, c)
        elif isinstance(tree, WikiDivTree):
            for c in tree:
                self.convert(fp, c)
            fp.write('\n')
        elif isinstance(tree, WikiTree):
            for c in tree:
                self.convert(fp, c)
        return


##  WikiLinkExtractor
##
class WikiLinkExtractor(WikiTextParser):

    def __init__(self, errfp=sys.stderr, codec='utf-8'):
        WikiTextParser.__init__(self)
        self.errfp = errfp
        self.codec = codec
        return

    def error(self, s):
        self.errfp.write(s)
        return

    def invalid_token(self, pos, token):
        if self.errfp is not None:
            self.error('invalid token(%d): %r\n' % (pos, token))
        return

    def convert(self, fp, tree=None):
        if tree is None:
            self.convert(fp, self.get_root())
        elif isinstance(tree, WikiKeywordTree):
            if tree:
                if isinstance(tree[0], WikiTree):
                    name = tree[0].get_text()
                else:
                    name = tree[0]
                if isinstance(name, unicode):
                    fp.write('keyword\t'+name.encode(self.codec, 'ignore'))
                    if 2 <= len(tree) and not isignored(name):
                        text = tree[-1].get_text()
                        fp.write('\t'+text.encode(self.codec, 'ignore'))
                    fp.write('\n')
        elif isinstance(tree, WikiLinkTree):
            if tree:
                if isinstance(tree[0], WikiTree):
                    url = tree[0].get_text()
                else:
                    url = tree[0]
                if isinstance(url, unicode):
                    fp.write('link\t'+url.encode(self.codec, 'ignore'))
                    if 2 <= len(tree):
                        text = tree[-1].get_text()
                        fp.write('\t'+text.encode(self.codec, 'ignore'))
                    fp.write('\n')
        elif isinstance(tree, WikiTree):
            for c in tree:
                self.convert(fp, c)
        return


##  MWDump2Text
##
class MWDump2Text(MWXMLDumpFilter):

    def __init__(self, factory,
                 outfp=sys.stdout, codec='utf-8', titleline=True,
                 titlepat=None, revisionlimit=1):
        MWXMLDumpFilter.__init__(
            self,
            titlepat=titlepat, revisionlimit=revisionlimit)
        self.factory = factory
        self.codec = codec
        self.outfp = outfp
        self.titleline = titleline
        return

    def open_file(self, pageid, title, revision):
        print >>sys.stderr, (title,revision)
        if self.titleline:
            self.write(title+'\n')
        self._textparser = self.factory(self.codec)
        return self.outfp
    
    def write_file(self, fp, text):
        self._textparser.feed_text(text)
        return
    
    def close_file(self, fp):
        self._textparser.close()
        self._textparser.convert(fp)
        self.write('\f\n')
        return


##  MWCDB2Text
##
class MWCDB2Text(object):

    def __init__(self, srcpath, dstpath, factory):
        self.reader = CDBReader(srcpath)
        self.writer = CDBMaker(dstpath)
        self.factory = factory
        return

    def close(self):
        self.writer.finish()
        return

    def convert(self, pageid, revision=0):
        key = '%d/%d:text' % (pageid, revision)
        srcbuf = StringIO(self.reader[key])
        src = GzipFile(mode='r', fileobj=srcbuf)
        dstbuf = StringIO()
        dst = GzipFile(mode='w', fileobj=dstbuf)
        textparser = self.factory('utf-8')
        textparser.feed_text(src.read().decode('utf-8'))
        textparser.close()
        textparser.convert(dst)
        src.close()
        dst.close()
        self.writer.add(key, dstbuf.getvalue())
        key = '%d:title' % pageid
        self.writer.add(key, self.reader[key])
        return

    def convert_all(self):
        for key in self.reader:
            (id,_,type) = key.partition(':')
            if type != 'text': continue
            try:
                (pageid,_,revision) = id.partition('/')
                pageid = int(pageid)
                revision = int(revision)
            except ValueError:
                continue
            print >>sys.stderr, (pageid,revision)
            self.convert(pageid, revision)
        return


# main
def main(argv):
    import getopt
    def getfp(path, mode='r'):
        if path == '-' and mode == 'r':
            return sys.stdin
        elif path == '-' and mode == 'w':
            return sys.stdout
        elif path.endswith('.gz'):
            return GzipFile(path, mode=mode)
        elif path.endswith('.bz2'):
            return BZ2File(path, mode=mode)
        else:
            return open(path, mode=mode+'b')
    def usage():
        print ('usage: %s [-X xmldump] [-C cdbdump] [-o output] [-c codec] [-T] [-L] '
               '[-e titlepat] [-r revisionlimit] [file ...]') % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'X:C:o:c:TLe:r:')
    except getopt.GetoptError:
        return usage()
    xmldump = None
    cdbdump = None
    output = None
    codec = 'utf-8'
    titlepat = None
    revisionlimit = 1
    titleline = False
    factory = (lambda codec: WikiTextExtractor(codec=codec))
    for (k, v) in opts:
        if k == '-X': xmldump = v
        elif k == '-C': cdbdump = v
        elif k == '-o': output = v
        elif k == '-c': codec = v 
        elif k == '-T': titleline = True
        elif k == '-L': factory = (lambda codec: WikiLinkExtractor(codec=codec))
        elif k == '-e': titlepat = re.compile(v)
        elif k == '-r': revisionlimit = int(v)
    if xmldump is not None:
        outfp = getfp(output or '-', 'w')
        parser = MWDump2Text(
            factory, outfp=outfp,
            codec=codec, titleline=titleline,
            titlepat=titlepat, revisionlimit=revisionlimit)
        fp = getfp(xmldump)
        parser.feed_file(fp)
        fp.close()
        parser.close()
    elif cdbdump is not None:
        if not output: return usage()
        reader = MWCDB2Text(cdbdump, output, factory)
        if args:
            for pageid in args:
                reader.convert(int(pageid))
        else:
            try:
                reader.convert_all()
            finally:
                reader.close()
    else:
        outfp = getfp(output or '-', 'w')
        for path in (args or ['-']):
            parser = factory(codec)
            fp = getfp(path)
            parser.feed_file(fp)
            fp.close()
            parser.close()
            parser.convert(outfp)
    return

if __name__ == '__main__': sys.exit(main(sys.argv))
