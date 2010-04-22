
from sit import *
from writer import Writer


class CGState(object):

    o = None

    module = None

    def __init__(self, writer):
        self.o = writer



BASIC_TYPES = {
    'byte'  : None,
    'short' : None,
    'int'   : None,
    'long'  : None,
    'ubyte' : None,
    'ushort': None,
    'uint'  : None,
    'ulong' : None,

    'float' : None,
    'double': None,
    'real'  : None,

    'char'  : None,
    'wchar' : None,
    'dchar' : None,

    'bool'  : None,
    'size_t': None,
    'string': None,
}



class CGSemVisitor(SemVisitor):

    targetPath = None
    package = None

    def __init__(self):
        super(CGSemVisitor, self).__init__()


    def defaultVisit(self, node, st):
        assert False, "unimplemented visit for %r" % node


    def unimpl(self, node, st):
        st.o.fl("/* unimplemented %s */", type(node).__name__)


    def visitSemModule(self, node, st):
        (st.o
         .pl("/* Generated by minidic */")
         .fl("module %s.%s;", self.package, node.fqi)
         .l()
         .fl('static import %s;', node.fqi)
         .pl('static import md = minid.api;')
         .pl('static import mdu = minid.util;')
         .pl('static import mdi = minidic.binding;')
         .l()
         )

        self.generateModuleInit(node, st)

        st.module = node

        for decl in node.decls:
            self.visit(decl, st)


    def visitSemImportDecl(self, node, st):
        (st.o
         .fl('import %s.%s : MD_%s;', self.package, node.module, node.symbol)
         )


    def visitSemConstDecl(self, node, st):
        self.unimpl(node, st)


    def visitSemClassDecl(self, node, st):
        self.generateAggregate(node, st)


    def generateAggregate(self, node, st):
        class_fqn = st.module.fqi + '.' + node.ident
        is_class = isinstance(node, SemClassDecl)
        
        (st.o
         .fl('struct MD_%s', node.ident)
         .push('{')
         .pop().fl('static:').push()
         .fl('const Name = "%s";', node.ident)
         .fl('const FQName = "%s";', class_fqn)
         .l()
         .fl('/// Reference to the MiniD class')
         .fl('ulong classRef = ulong.max;')
         .l()
         )
        
        if is_class:
            (st.o
             .fl('enum : bool { WrapStruct = false }')
             .fl('alias %s RawWrapRef;', class_fqn)
             .fl('alias %s Wrap;', class_fqn)
             )
        else:
            (st.o
             .fl('enum : bool { WrapStruct = true }')
             .fl('alias %s* RawWrapRef;', class_fqn)
             .fl('alias StructBox!(%s) Wrap;', class_fqn)
             )
            
        (st.o
         .l()
         )

        # init
        (st.o
         .pl('void init(md.MDThread* t)')
         .push('{')
         .pl('md.CreateClass(t, FQName, (md.CreateClass* c)')
         .push('{')
         .pl('c.method("constructor", &constructor);')
         )
        self.generateInitMethodBinds(node, st)
        (st.o
         .pop('});')
         .l()
         .pl('md.newFunction(t, &allocator, "allocator");')
         .pl('md.setAllocator(t, -2);')
         .l()
         .pl('classRef = md.createRef(t, -1);')
         .pl('assert( classRef != classRef.max );')
         .l()
         .pl('md.newGlobal(t, Name);')
         .pop('}')
         .l()
         )
        
        # initModule
        (st.o
         .pl('void init(md.MDThread* t)')
         .push('{')
         .pl('if( classRef == classRef.max )')
         .push().pl('init(t);').pop()
         .l()
         .pl('md.pushRef(t, classRef);')
         .pl('md.newGlobal(t, Name);')
         .pop('}')
         .l()
         )
        
        # checkInstParam
        (st.o
         .pl('void checkInstParam(md.MDThread* t, md.word slot = 0)')
         .push('{')
         .pl('mdu.checkInstParamRef(t, slot, classRef)')
         .pop('}')
         .l()
         )
        
        # getWrap
        (st.o
         .pl('Wrap getWrap(md.MDThread* t, md.word slot = 0)')
         .push('{')
         .pl('Object r = null;')
         .pl('md.stackCheck(t,')
         .push('{')
         .pl('md.getExtraVal(t, slot, 0);')
         .pl('if( !md.isNull(t, -1) )')
         .push().pl('r = md.getNativeObj(t, -1);').pop()
         .pl('md.pop(t);')
         .pop('});')
         .pl('return cast(Wrap) r;')
         .pop('}')
         .l()
         )
        
        # setWrap
        (st.o
         .pl('void setWrap(md.MDThread* t, Wrap obj, md.word slot = 0)')
         .push('{')
         .pl('md.stackCheck(t,')
         .push('{')
         .pl('md.pushNativeObj(t, obj);')
         .pl('md.setExtraVal(t, slot<0?slot-1:slot, 0);')
         .pop('});')
         .pop('}')
         .l()
         )
        
        # pushPtr
        (st.o
         .pl('void pushPtr(MDThread* t, void* ptr)')
         .push('{')
         .pl('create(t, cast(RawWrapRef)(*cast(Object*) ptr));'
             if is_class else
             'create(t, cast(RawWrapRef) ptr);')
         .pop('}')
         .l()
         )
        
        # popValue
        (st.o
         .fl('%s popValue(MDThread* t)', class_fqn)
         .push('{')
         .pl('auto r = getWrap(t, -1);')
         .pl('pop(t);')
         .l()
         .pl('return r;'
             if is_class else
             'return r.value;')
         .pop('}')
         .l()
         )
        
        # create (slot)
        (st.o
         .pl('void create(md.MDThread* t, md.word slot = 0)')
         .push('{')
         .pl('create(t, slot, null, true);')
         .pop('}')
         .l()
         )
        
        # create (RawWrapRef)
        (st.o
         .pl('void create(md.MDThread* t, RawWrapRef obj)')
         .push('{')
         .pl('assert( classRef != classRef.max, '
             +'"classRef for "~FQName~" hasn\'t been set" );')
         # MDS: this ...
         .pl('auto slot = md.pushRef(t, classRef);')
         # MDS: this ... Class
         .pl('create(t, slot, obj, false);')
         # MDS: this ... Class Object
         .pl('md.swap(t);')
         # MDS: this ... Object Class
         .pl('md.pop(t);')
         # MDS: this ... Object
         .pop('}')
         .l()
         )
        
        # create (slot, RawWrapRef, hasArgs)
        (st.o
         .pl('void create(md.MDThread* t, md.word slot,'
             +' RawWrapRef obj, bool hasArgs)')
         .push('{')
         # MDS: this ...
         .pl('md.newInstance(t, slot, 1, 0);')
         # MDS: this ... Object
         .pl('md.stackCheck(t,')
         .push('{')
         .pl('if( obj !is null )')
         .push('{')
         # MDS: this ... Object
         .fl('md.pushNativeObj(t, %s);',
             ('obj' if is_class else 'new Wrap(*obj)'))
         # MDS: this ... Object NativeObj
         .pl('md.setExtraVal(t, -2, 0);')
         # MDS: this ... Object
         .pop('}')
         .pop('});')
         .l()
         # MDS: this ... Object
         .pl('md.dup(t);')
         # MDS: this ... Object Object
         .pl('md.pushNull(t);')
         # MDS: this ... Object Object null
         .l()
         .pl('if( hasArgs )')
         .push('{')
         # MDS: this ... Object Object null
         .pl('md.rotateAll(t, 3);')
         # MDS: this Object Object null ...
         .pl('md.methodCall(t, 2, "constructor", 0);')
         # MDS: this Object
         .pop('}')
         .pl('else')
         .push('{')
         # MDS: this ... Object Object null
         .pl('md.methodCall(t, -2, "constructor", 0);')
         # MDS: this ... Object
         .pop('}')
         .l()
         # MDS: this [...] Object
         .pl('md.stackCheck(t,')
         .push('{')
         .pl('md.getExtraVal(t, -1, 0);')
         # MDS: this [...] Object NativeObj
         .pl('assert( md.getNativeObj(t, -1) !is null );')
         .pl('md.pop(t);')
         # MDS: this [...] Object
         .pop('});')
         .pop('}')
         .l()
         )
        
        # allocator
        (st.o
         .pl('md.uword allocator(md.MDThread* t, md.uword numParams)')
         .push('{')
         .pl('create(t, 0);')
         .pl('return 1;')
         .pop('}')
         .l()
         )
        
        # constructor
        (st.o
         .pl('md.uword constructor(md.MDThread* t, md.uword numParams)')
         .push('{')
         .pl('mdu.checkInstParamRef(t, 0, classRef);')
         .pl('auto obj = getWrap(t);')
         .l()
         .pl('if( obj is null )')
         .push('{')
         .pl('md.stackCheck(t, delegate void()')
         .push('{')
         )
        self.generateCtor(node, st)
        (st.o
         .pop('});')
         .fl('assert( obj !is null, "%s constructor didn\'t'
             +' initialise an object" );', class_fqn)
         .pl('setWrap(t, obj);')
         .pop('}')
         .l()
         .pl('return 0;')
         .pop('}')
         .l()
         )

        # Visit declarations
        for decl in node.decls:
            self.visit(decl, st)

        (st.o
         .pop('}')
         )


    def visitSemStructDecl(self, node, st):
        self.unimpl(node, st)


    def visitSemRoDecl(self, node, st):
        (st.o
         .fl('md.uword method_%s(md.MDThread* t, md.uword numParams)',
             node.ident)
         .push('{')
         .pl('mdu.checkInstParamRef(t, 0, classRef);')
         .pl('auto obj = getWrap(t);')
         .l()
         .pl('if( numParams > 0 )')
         .push('{')
         .fl('md.throwException(t, "property \'%s\' is read-only");',
             node.ident)
         .pl('assert(false);')
         .pop('}')
         .l()
         .pl('md.stackCheck(t, 1, delegate void()')
         .push('{')
         )
        self.generateTypePush(node.type, "obj.%s" % node.ident, st)
        (st.o
         .pop('});')
         .l()
         .pl('return 1;')
         .pop('}')
         .l()
         )


    def visitSemRwDecl(self, node, st):
        (st.o
         .fl('md.uword method_%s(md.MDThread* t, md.uword numParams)',
             node.ident)
         .push('{')
         .pl('mdu.checkInstParamRef(t, 0, classRef);')
         .pl('auto obj = getWrap(t);')
         .l()
         .pl('if( numParams == 0 )')
         .push('{')
         .pl('md.stackCheck(t, 1, delegate void()')
         .push('{')
         )
        self.generateTypePush(node.type, "obj.%s" % node.ident, st)
        (st.o
         .pop('});')
         .pl('return 1;')
         .pop('}')
         .pl('else if( numParams == 1 )')
         .push('{')
         .pl('md.stackCheck(t, 0, delegate void()')
         .push('{')
         )
        (st.o
         .fl('auto val = (%s);', self.generateTypeRead(node.type, 1, st))
         .fl('obj.%s = val;', node.ident)
         )
        (st.o
         .pop('});')
         .pl('return 0;')
         .pop('}')
         .pl('else')
         .push('{')
         .fl('md.throwException(t, "property \'%s\' should be called with zero or one arguments");',
             node.ident)
         .pl('assert(false);')
         .pop('}')
         .pop('}')
         .l()
         )


    def visitSemFuncDecl(self, node, st):
        (st.o
         .fl('md.uword method_%s(md.MDThread* t, md.uword numParams)',
             node.ident)
         .push('{')
         .pl('mdu.checkInstParamRef(t, 0, classRef);')
         .pl('auto obj = getWrap(t);')
         .l()
         )

        void_ret = False

        if (isinstance(node.returnType, SemSymbolType)
                and node.returnType.ident == 'void'):
            void_ret = True

        (st.o
         .fl('md.stackCheck(t, %d, delegate void()', 0 if void_ret else 1)
         .push('{')
         .fl('if( numParams != %d )', len(node.args))
         .push('{')
         # TODO: build usage string
         .fl('md.throwException(t, "Bad arguments to %s");', node.ident)
         .pl('assert(false);')
         .pop('}')
         .l()
         )

        for i,arg in enumerate(node.args):
            if arg.isRef:
                st.o.fl('/* TODO: ref arg %s */', arg.ident)
            if arg.isOut:
                st.o.fl('/* TODO: out arg %s */', arg.ident)
            if arg.isLazy:
                st.o.fl('/* TODO: lazy arg %s */', arg.ident)
            self.generateTypeCheck(arg.type, i+1, st)

        for i,arg in enumerate(node.args):
            st.o.fl('auto __arg_%d = (%s);', i,
                    self.generateTypeRead(arg.type, i+1, st))

        call = 'obj.%s(%s)' % (
            node.ident,
            ", ".join(("__arg_%d" % i) for i in xrange(len(node.args))))

        if void_ret:
            st.o.fl('%s;', call)

        else:
            st.o.fl('auto result = %s;', call)
            self.generateTypePush(node.returnType, 'result', st)
        
        (st.o
         .pop('}')
         )
        
        (st.o
         .fl('return %d;', 0 if void_ret else 1)
         .pop('}')
         .l()
         )


    def visitSemOpDecl(self, node, st):
        self.unimpl(node, st)


    def visitSemMixin(self, node, st):
        st.o.r(node.code)


    def generateModuleInit(self, node, st):
        (st.o
         .pl('struct MD_Module')
         .push('{')
         .pop().pl('static:').push()
         .pl('void init(MDThread* t)')
         .push('{')
         )

        for decl in node.decls:
            if isinstance(decl, SemMixin): continue
            if isinstance(decl, SemImportDecl): continue
            st.o.fl('MD_%s.init(t);', decl.ident)
        
        (st.o
         .l()
         .fl('md.makeModule(t, "%s", function uword(MDThread* t,'
             +' uword numParams)', node.fqi)
         .push('{')
         )

        for decl in node.decls:
            if isinstance(decl, SemMixin): continue
            if isinstance(decl, SemImportDecl): continue
            st.o.fl('MD_%s.initModule(t);', decl.ident)
        
        (st.o
         .pl('return 0;')
         .pop('});')
         .pop('}')
         .pop('}')
         .l()
         )


    def generateCtor(self, node, st):
        class_fqn = st.module.fqi + '.' + node.ident
        is_class = isinstance(node, SemClassDecl)

        # We need to deal with the possibility of there being multiple
        # constructors available.
        #
        # The way we handle this is by checking whether we can call each
        # ctor based on the number of arguments and the type of arguments.

        # Sort the list of ctors.
        
        ctors = sorted(node.ctors,
                       cmp = lambda a,b: cmp(len(a.args),len(b.args)))

        # If there are no ctors at all, insert code to prevent this type from
        # being constructed from within MiniD.

        if len(ctors) == 0:
            (st.o
             .pl('if( obj is null )')
             .push('{')
             .fl('md.throwException(t, "Cannot create %s objects");', node.ident)
             .pl('assert(false);')
             .pop('}')
             )
            return

        # Start processing the ctors

        def doCtor(ctor):
            (st.o
             .fl('if( numParams == %d )', len(ctor.args))
             .push('{')
             )

            for i,arg in enumerate(ctor.args):
                self.generateTypeCheck(arg.type, i+1, st)

            for i,arg in enumerate(ctor.args):
                st.o.fl('auto __arg_%d = (%s);', i,
                        self.generateTypeRead(arg.type, i+1, st))

            if is_class:
                st.o.fl('obj = new %s(%s)', class_fqn,
                        ','.join('__arg_%d'%i for i in range(len(ctor.args))))

            else:
                st.o.fl('%s __struct;', class_fqn)
                for i,arg in enumerate(ctor.args):
                    st.o.fl('__struct.%s = __arg_%d', arg.ident, i)

                st.o.pl('obj = new Wrap(__struct);')
            
            st.o.pop('}')

        (st.o
         .fl('if( numParams > %d )', max(len(ctor.args) for ctor in ctors))
         .push('{')
         # TODO: build usage string
         .pl('throwException(t, "Bad arguments to constructor");')
         .pl('assert(false);')
         .pop('}')
         )
        
        for ctor in ctors:
            st.o.p('else ')
            doCtor(ctor)

        (st.o
         .pl('else')
         .push().pl('assert(false);').pop()
         )


    def generateTypeCheck(self, ty, slot, st):
        if isinstance(ty, SemSymbolType) and ty.ident in BASIC_TYPES:
            ident = ty.ident

            if ident == 'ulong':
                assert False, "%s: ulongs not supported" % ty.src

            if ident == 'bool':
                st.o.fl('md.checkBoolParam(t, %r);', slot)

            elif ident in ('byte', 'short', 'int', 'long',
                           'ubyte', 'ushort', 'uint'):
                st.o.fl('md.checkIntParam(t, %r);', slot)

            elif ident in ('float', 'double', 'real'):
                st.o.fl('md.checkFloatParam(t, %r);', slot)

            elif ident in ('char', 'wchar', 'dchar'):
                st.o.fl('md.checkCharParam(t, %r);', slot)

            elif ident == 'string':
                st.o.fl('md.checkStringParam(t, %r);', slot)

            elif ident == 'size_t':
                st.o.fl('md.checkIntParam(t, %r);', slot)

            else:
                assert False

        elif isinstance(ty, SemSymbolType):
            ident = ty.ident
            st.o.fl('MD_%s.checkInstParam(t, %d);', ident, slot)

        else:
            st.o.fl('unimplemented/* type check %s, %d */;', ty, slot)


    def generateTypeRead(self, ty, slot, st):
        if isinstance(ty, SemSymbolType) and ty.ident in BASIC_TYPES:
            ident = ty.ident

            if ident == 'ulong':
                assert False, "%s: ulongs not supported" % ty.src

            if ident == 'bool':
                return 'md.checkBoolParam(t, %r)' % slot

            elif ident in ('byte', 'short', 'int', 'long',
                           'ubyte', 'ushort', 'uint'):
                return 'to!(%s)(md.checkIntParam(t, %r))' % (ident,slot)

            elif ident in ('float', 'double', 'real'):
                return 'cast(%s)md.checkFloatParam(t, %r)' % (ident,slot)

            elif ident in ('char', 'wchar', 'dchar'):
                return 'to!(%s)(md.checkCharParam(t, %r))' % (ident,slot)

            elif ident == 'string':
                return 'md.checkStringParam(t, %r)' % slot

            elif ident == 'size_t':
                return 'to!(size_t)(md.checkIntParam(t, %r))' % slot

            else:
                assert False

        elif isinstance(ty, SemSymbolType):
            ident = ty.ident
            return 'MD_%s.getWrap(t, %d)' % (ident, slot)

        else:
            return 'unimplemented/* type read %s, %d */' % (ty, slot)


    def generateTypePush(self, ty, value, st):
        if isinstance(ty, SemSymbolType) and ty.ident in BASIC_TYPES:
            ident = ty.ident

            if ident == 'ulong':
                assert False, "%s: ulongs not supported" % ty.src

            if ident == 'bool':
                st.o.fl('md.pushBool(t, (%s));', value)

            elif ident in ('byte', 'short', 'int', 'long',
                           'ubyte', 'ushort', 'uint'):
                st.o.fl('md.pushInt(t, (%s));', value)

            elif ident in ('float', 'double', 'real'):
                st.o.fl('md.pushFloat(t, (%s));', value)

            elif ident in ('char', 'wchar', 'dchar'):
                st.o.fl('md.pushChar(t, (%s));', value)

            elif ident == 'string':
                st.o.fl('md.pushString(t, (%s));', value)

            elif ident == 'size_t':
                st.o.fl('md.pushInt(t, to!(long)(%s));', value)

            else:
                assert False

        elif isinstance(ty, SemSymbolType):
            ident = ty.ident
            st.o.fl('MD_%s.create(t, %s);', ident, value)

        elif isinstance(ty, SemArrayType):
            ety = ty.elemType
            est = isinstance(ety, SemSymbolType)
            if not est:
                st.o.fl('static assert(false, "unimplemented: '
                        +'nested array push");')
                return

            if est and ety.ident in BASIC_TYPES:
                ident = ety.ident

                if ident == 'ulong':
                    assert False, "%s: ulongs not supported" % ty.src

                st.o.fl('mdi.NativeArray.createFrom(t, value);')

            elif est:
                st.o.fl('mdi.NativeArray.createFrom(t, value,'
                        +' &MD_%s.pushPtr);', ety.ident)

        else:
            st.o.fl('unimplemented/* type push %s, (%s) */;', ty, value)


    def generateInitMethodBinds(self, node, st):
        for decl in node.decls:
            if decl.ident == "this": continue

            if isinstance(decl, SemMixin):
                # do nothing
                pass

            elif isinstance(decl, SemOpDecl):
                st.o.fl('/* unimplemented init method bind for op %s */', decl.ident)

            else:
                st.o.fl('c.method("%s", &method_%s);', decl.ident, decl.ident)


