import cgi

__author__ = 'Jeremy Latt <jlatt@yelp.com>'
__all__ = ('T', 'Literal', 'Text', 'XHTML')

def iterflat(args):
    for arg in args:
        if hasattr(arg, '__iter__'):
            for a in iterflat(arg):
                yield a
        else:
            yield arg

def translate(attrs):
    for key, value in attrs.iteritems():
        if key.endswith('_'):
            key = key[:-1]

        yield (key, value)

def iterattrs(attrs):
    for key, value in attrs.iteritems():
        if isinstance(value, bool):
            if value:
                value = key
            else: # skip False
                continue
        else:
            value = unicode(value)

        yield (key, value)

class StrSerializable(object):
    def __unicode__(self):
        from StringIO import StringIO
        f = self.serialize(StringIO())
        strval = f.getvalue()
        f.close()
        return strval

    def __str__(self):
        return unicode(self).encode('utf-8')
    
    __repr__ = __str__

    def serialize(self, f):
        raise NotImplemented

class _Tag(StrSerializable):
    empty = set(('link', 'input', 'hr', 'meta'))

    def __init__(self, tagname, *children, **attrs):
        assert tagname == cgi.escape(tagname), 'illegal tag name %s' % tagname

        self.tagname = tagname
        self.children = list(iterflat(children))
        self.attrs = dict(translate(attrs))

    def __call__(self, *children, **attrs):
        if children:
            self.children.extend(iterflat(children))
        if attrs:
            self.attrs.update(translate(attrs))
        return self

    def serialize(self, f):
        is_empty = self.tagname in self.empty
        open_tag_end = '>'
        if is_empty:
            assert not self.children, 'empty tag %s has children' % self.tagname
            open_tag_end = '/>'

        # open tag
        formatted_attrs = ''.join([' %s="%s"' % (cgi.escape(key), cgi.escape(value, quote=True)) for key, value in iterattrs(self.attrs)])
        f.write('<%s%s%s' % (self.tagname, formatted_attrs, open_tag_end))

        for child in self.children:
            if hasattr(child, 'serialize'):
                child.serialize(f)
            else:
                f.write(cgi.escape(unicode(child)))
        
        if not is_empty:
            f.write('</%s>' % self.tagname)

        return f

class Literal(StrSerializable):
    def __init__(self, html):
        self.html = unicode(html)

    def serialize(self, f):
        f.write(self.html)
        return f

class Text(StrSerializable):
    def __init__(self, text):
        self.text = unicode(text)

    def serialize(self, f):
        f.write(cgi.escape(self.text))
        return f

class CData(StrSerializable):
    begin = '<![CDATA['
    end = ']]>'

    def __init__(self, value):
        self.value = unicode(value)

    def serialize(self, f):
        f.write(self.begin)
        f.write(self.value)
        f.write(self.end)
        return f

class ScriptCData(CData):
    begin = '/* %s */' % CData.begin
    end = '/* %s */' % CData.end

class XHTML(StrSerializable):
    preamble = '<?xml version="1.0" encoding="UTF-8"?>'
    namespace = 'http://www.w3.org/1999/xhtml'
    strict_doctype = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'

    def __init__(self):
        self.html = T.html(xmlns=self.namespace)

    def serialize(self, f):
        f.write(self.preamble)
        f.write(self.strict_doctype)
        self.html.serialize(f)
        return f

    def __call__(self, *args, **kw):
        self.html(*args, **kw)
        return self

class TagFactory(object):
    """Tag wrapper that lets you use normal Tag syntax (i.e. T('head')(...)) as
    well as "manifested" syntax like T.head(...).
    """

    tag_cls = _Tag

    def __getattr__(self, name):
        return self.tag_cls(name)

    def __call__(self, *args, **kwargs):
        return self.tag_cls(*args, **kwargs)

T = TagFactory()
