
from sit import *
from writer import Writer


class CGState(object):

    o = None

    module = None

    typeIsClass = None

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

# Operators that map to 'op' + themselves with the first letter capitalised.
# These are the same in both MiniD and D.

OP_SELF = """
    index indexAssign
    slice sliceAssign
    call
    cmp equals
    neg com inc dec
""".split()

# Binary operators: all of these have _r and Assign variants.

OP_SELF_BIN = """
    cat add sub mul div mod and or xor shl shr uShr
""".split()

# Operators which map to something other than themselves in either MiniD or D.
# Elements are: mdi_name : (d_name, minid_name)

OP_MAP = {
    'in': ('opIn_r', 'opIn'),
}

# Operators which require special handling.

OP_SPECIAL = (
    'length', 'lengthAssign',
)



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
         .fl("module %s%s;",
             (self.package+"." if self.package is not None else ''),
             node.fqi)
         .l()
         )
        
        if self.package is not None:
            # Without a package, this would simply import ourselves.
            st.o.fl('static import %s;', node.fqi)
            
        (st.o
         .pl('static import md = minid.api;')
         .pl('static import mdu = minid.utils;')
         .pl('static import mdi = minidic.binding;')
         .pl('import tango.util.Convert : to;')
         .l()
         )

        self.generateModuleInit(node, st)

        st.module = node

        for decl in node.decls:
            self.visit(decl, st)


    def visitSemPackage(self, node, st):
        (st.o
         .pl('/* Generated by minidic */')
         .fl('module %s%s.__package__;',
             (self.package+'.' if self.package is not None else ''),
             node.fqi)
         .l()
         )
            
        (st.o
         .pl('static import md = minid.api;')
         .pl('static import mdu = minid.utils;')
         .pl('static import mdi = minidic.binding;')
         .l()
         )

        for decl in (d for d in node.decls if isinstance(d, SemImportDecl)):
            st.o.fl('static import %s%s%s;',
                    (self.package+'.' if self.package is not None else ''),
                    decl.module,
                    ('.__package__' if decl.isPackage else ''))

        self.generatePackageInit(node, st)


    def visitSemImportDecl(self, node, st):
        (st.o
         .fl('import %s%s : MD_%s;',
             (self.package+"." if self.package is not None else ''),
             node.module, node.symbol)
         )


    def visitSemConstDecl(self, node, st):
        sym_fqn = "%s.%s" % (st.module.fqi, node.ident)
        if self.package is None:
            sym_fqn = node.ident
        
        (st.o
         .fl('struct MD_%s', node.ident)
         .push('{')
         .pop().fl('static:').push()
         .fl('void initModule(md.MDThread* t)')
         .push('{')
         .do(self.generateTypePush(
             node.type, sym_fqn, st))
         .fl('md.newGlobal(t, "%s");', node.ident)
         .pop('}')
         .pop('}')
         .l()
         )


    def visitSemClassDecl(self, node, st):
        self.generateAggregate(node, st)


    def visitSemStructDecl(self, node, st):
        self.generateAggregate(node, st)


    def generateAggregate(self, node, st):
        class_fqn = st.module.fqi + '.' + node.ident
        class_fqn_md = class_fqn
        is_class = isinstance(node, SemClassDecl)

        if node.nativeLocal or self.package is None:
            class_fqn = node.ident

        old_typeIsClass = st.typeIsClass
        st.typeIsClass = is_class
        
        (st.o
         .fl('struct MD_%s', node.ident)
         .push('{')
         .pop().fl('static:').push()
         .fl('const Name = "%s";', node.ident)
         .fl('const FQName = "%s";', class_fqn_md)
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
             .fl('alias mdi.StructBox!(%s) Wrap;', class_fqn)
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
         # TODO: is this actually needed?
         .pl('md.newGlobal(t, Name);')
         .pop('}')
         .l()
         )
        
        # initModule
        (st.o
         .pl('void initModule(md.MDThread* t)')
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
         .pl('mdi.checkInstParamRef(t, slot, classRef);')
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

        # getValue
        (st.o
         .fl('%s getValue(md.MDThread* t, md.word slot = 0)', class_fqn)
         .push('{')
         .pl('auto wrap = getWrap(t, slot);')
         .pl('return wrap;'
             if is_class else
             'return wrap.value;')
         .pop('}')
         .l()
         )
        
        # pushPtr
        (st.o
         .pl('void pushPtr(md.MDThread* t, void* ptr)')
         .push('{')
         .pl('create(t, cast(RawWrapRef)(*cast(Object*) ptr));'
             if is_class else
             'create(t, cast(RawWrapRef) ptr);')
         .pop('}')
         .l()
         )
        
        # popValue
        (st.o
         .fl('%s popValue(md.MDThread* t)', class_fqn)
         .push('{')
         .pl('auto r = getWrap(t, -1);')
         .pl('md.pop(t);')
         .l()
         .pl('return r;'
             if is_class else
             'return r.value;')
         .pop('}')
         .l()
         )

        # popPtr
        (st.o
         .pl('void popPtr(md.MDThread* t, void* ptr)')
         .push('{')
         )
        if is_class:
            st.o.pl('*(cast(RawWrapRef*)(ptr)) = popValue(t);')
        else:
            st.o.pl('*(cast(RawWrapRef)(ptr)) = popValue(t);')
        (st.o
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

        # create (*RawWrapRef) (structs only)
        if not is_class:
            (st.o
             .pl('void create(md.MDThread* t, typeof(*RawWrapRef) obj)')
             .push('{')
             .pl('create(t, &obj);')
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
         .pl('mdi.checkInstParamRef(t, 0, classRef);')
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
         .l()
         )

        st.typeIsClass = old_typeIsClass


    def visitSemEnumDecl(self, node, st):
        class_fqn = st.module.fqi + '.' + node.ident
        class_fqn_md = class_fqn

        prefix = (st.module.fqi + '.' + node.ident + '.'
                  if not node.flat
                  else st.module.fqi + '.')
        
        (st.o
         .fl('struct MD_%s', node.ident)
         .push('{')
         .pop().fl('static:').push()
         .fl('const Name = "%s";', node.ident)
         .fl('const FQName = "%s";', class_fqn_md)
         .l()
         )

        # init
        (st.o
         .pl('void init(md.MDThread* t)')
         .pl('{')
         .pl('}')
         .l()
         )

        # initModule
        (st.o
         .pl('void initModule(md.MDThread* t)')
         .push('{')
         .pl('auto ns = md.newNamespace(t, FQName);')
         .l()
         .pl('md.newFunction(t, &method_toString, "toString");')
         .pl('md.fielda(t, ns, "toString");')
         .l()
         )

        if node.flat:
            (st.o
             .pl('md.newGlobal(t, Name);')
             )

            for member in node.members:
                (st.o
                 .fl('md.pushInt(t, %s);', prefix+member)
                 .fl('md.newGlobal(t, "%s");', member)
                 )

            (st.o
             .pop('}')
             .l()
             )

        else:
            for member in node.members:
                (st.o
                 .fl('md.pushInt(t, %s);', prefix+member)
                 .fl('md.fielda(t, ns, "%s");', member)
                 )

            (st.o
             .pl('md.newGlobal(t, Name);')
             .pop('}')
             .l()
             )

        # getValue
        (st.o
         .fl('%s getValue(md.MDThread* t, md.word slot = 0)', class_fqn)
         .push('{')
         .fl('return to!(%s)(md.getInt(t, slot));', class_fqn)
         .pop('}')
         .l()
         )

        # popValue
        (st.o
         .fl('%s popValue(md.MDThread* t)', class_fqn)
         .push('{')
         .pl('auto r = getValue(t, -1);')
         .pl('md.pop(t);')
         .pl('return r;')
         .pop('}')
         .l()
         )

        # pushPtr
        (st.o
         .pl('void pushPtr(md.MDThread* t, void* ptr)')
         .push('{')
         .fl('create(t, *cast(%s*)(ptr));', class_fqn)
         .pop('}')
         .l()
         )

        # popPtr
        (st.o
         .pl('void popPtr(md.MDThread* t, void* ptr)')
         .push('{')
         .fl('*(cast(%s*)(ptr)) = popValue(t);', class_fqn)
         .pop('}')
         .l()
         )

        # create (Type*)
        (st.o
         .fl('void create(md.MDThread* t, %s* ptr)', class_fqn)
         .push('{')
         .pl('create(t, *ptr);')
         .pop('}')
         .l()
         )

        # create (Type)
        (st.o
         .fl('void create(md.MDThread* t, %s ptr)', class_fqn)
         .push('{')
         .pl('md.pushInt(t, ptr);')
         .pop('}')
         .l()
         )

        # method_toString
        (st.o
         .pl('md.uword method_toString(md.MDThread* t, md.uword numParams)')
         .push('{')
         .pl('auto v = getValue(t, 1);')
         .pl('char[] s;')
         .pl('switch( v )')
         .push('{')
         )

        for member in node.members:
            (st.o
             .fl('case %s: s = "%s"; break;', prefix+member, member)
             )

        (st.o
         .pl('default:')
         .push().pl('md.throwException(t, "Unknown "~Name~": \'{}\'", v);').pop()
         .pop('}')
         .pl('md.pushString(t, s);')
         .pl('return 1;')
         .pop('}')
         .l()
         )

        (st.o
         .pop('}')
         .l()
         )


    def visitSemRoDecl(self, node, st):
        (st.o
         .fl('md.uword method_%s(md.MDThread* t, md.uword numParams)',
             node.ident)
         .push('{')
         .pl('mdi.checkInstParamRef(t, 0, classRef);')
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
        self.generateTypePush(node.type, "obj%s.%s" % (
            ('' if st.typeIsClass else '.value'),
            node.ident), st)
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
         .pl('mdi.checkInstParamRef(t, 0, classRef);')
         .pl('auto obj = getWrap(t);')
         .l()
         .pl('if( numParams == 0 )')
         .push('{')
         .pl('md.stackCheck(t, 1, delegate void()')
         .push('{')
         )
        self.generateTypePush(node.type, "obj%s.%s" % (
            ('' if st.typeIsClass else '.value'),
            node.ident), st)
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
         .fl('obj%s.%s = val;',
             ('' if st.typeIsClass else '.value'),
             node.ident)
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
        self.visitFunction(node, st)


    def visitSemOpDecl(self, node, st):
        self.visitFunction(node, st)


    def visitSemOverloadDecl(self, node, st):
        self.visitFunction(node, st, node.overloads)


    def visitFunction(self, node, st, overloads=None):
        if overloads is None:
            overloads = (node,)
        
        isOp = isinstance(node, SemOpDecl) or (
            isinstance(node, SemOverloadDecl) and node.type is SemOpDecl)
        isFunc = not isOp

        d_name, md_name = None, None

        if isFunc:
            d_name = node.ident
            md_name = node.ident

        elif isOp:
            d_name, md_name = self.getOpNames(node)

        else:
            assert False

        prefix = ('method' if isFunc else
                  'op_method' # if isOp
                  )

        (st.o
         .fl('md.uword %s_%s(md.MDThread* t, md.uword numParams)',
             prefix, node.ident)
         .push('{')
         .pl('mdi.checkInstParamRef(t, 0, classRef);')
         .pl('auto obj = getWrap(t);')
         .l()
         )

        for overload in overloads:
            # If we've got a body mixin, just dump that in.
            if overload.body is not None:
                (st.o
                 .push('{')
                 .do(self.visit(overload.body, st))
                 .pop('}')
                 )
                continue
            
            void_ret = False

            if (isinstance(overload.returnType, SemSymbolType)
                    and overload.returnType.ident == 'void'):
                void_ret = True

            (st.o
             .fl('if( numParams == %d )', len(overload.args))
             .push('{')
             )

            # TODO: need to work out how to do type checks such that they
            # don't throw an exception: we want to try another overload if
            # the given types don't match.

            (st.o
             .fl('md.stackCheck(t, %d, delegate void()', 0 if void_ret else 1)
             .push('{')
             )

            for i,arg in enumerate(overload.args):
                ident = arg.ident
                if ident is None: ident = "__op_arg_%d" % i
                
                if arg.isRef:
                    st.o.fl('/* TODO: ref arg %s */', arg.ident)
                if arg.isOut:
                    st.o.fl('/* TODO: out arg %s */', arg.ident)
                if arg.isLazy:
                    st.o.fl('/* TODO: lazy arg %s */', arg.ident)
                    
                self.generateTypeCheck(arg.type, i+1, st)

            for i,arg in enumerate(overload.args):
                st.o.fl('auto __arg_%d = (%s);', i,
                        self.generateTypeRead(arg.type, i+1, st))

            call = 'obj%s.%s(%s)' % (
                ('' if st.typeIsClass else '.value'),
                d_name,
                ", ".join(("__arg_%d" % i) for i in xrange(len(overload.args))))

            if void_ret:
                st.o.fl('%s;', call)

            else:
                st.o.fl('auto result = %s;', call)
                self.generateTypePush(overload.returnType, 'result', st)
            
            (st.o
             .pop('});')
             .l()
             .fl('return %d;', 0 if void_ret else 1)
             .pop('}')
             .l()
             )

        # Fall-through if we didn't match any overloads
        # TODO: build usage string
        (st.o
         .fl('md.throwException(t, "Bad arguments to %s");', node.ident)
         .pl('assert(false);')
         .pop('}')
         .l()
         )


    def visitSemMixin(self, node, st):
        st.o.r(node.code).l()


    def generateModuleInit(self, node, st):
        (st.o
         .pl('struct MD_Module')
         .push('{')
         .pop().pl('static:').push()
         .pl('void init(md.MDThread* t)')
         .push('{')
         )

        for decl in node.decls:
            if isinstance(decl, SemMixin): continue
            if isinstance(decl, SemImportDecl): continue
            if isinstance(decl, SemConstDecl): continue
            st.o.fl('MD_%s.init(t);', decl.ident)
        
        (st.o
         .l()
         .fl('md.makeModule(t, "%s", function md.uword(md.MDThread* t,'
             +' md.uword numParams)', node.fqi)
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


    def generatePackageInit(self, node, st):
        (st.o
         .pl('struct MD_Module')
         .push('{')
         .pop().pl('static:').push()
         .pl('void init(md.MDThread* t)')
         .push('{')
         )

        for decl in node.decls:
            if not isinstance(decl, SemImportDecl): assert False
            st.o.fl('%s%s%s.MD_Module.init(t);',
                    (self.package+'.' if self.package else ''),
                    decl.module,
                    ('.__package__' if decl.isPackage else ''))

        (st.o
         .l()
         .fl('md.makeModule(t, "%s", function md.uword(md.MDThread* t,'
             +' md.uword numParams)', node.fqi)
         .push('{')
         )

        # I don't think this is needed.
        #for decl in node.decls:
        #    if not isinstance(decl, SemImportDecl): assert False
        #    st.o.fl('%s%s%s.MD_Module.initModule(t);',
        #            (self.package+'.' if self.package else ''),
        #            decl.module,
        #            ('.__package__' if decl.isPackage else ''))

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

        if node.nativeLocal or self.package is None:
            class_fqn = node.ident

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
                st.o.fl('obj = new %s(%s);', class_fqn,
                        ','.join('__arg_%d'%i for i in range(len(ctor.args))))

            else:
                st.o.fl('%s __struct;', class_fqn)
                st.o.fl('__struct = %s(%s);', class_fqn,
                        ','.join('__arg_%d'%i for i in range(len(ctor.args))))

                # This would be used if we wanted to be able to define
                # ctors that just fill in the struct for us.  Maybe enable
                # with an annotation?
                #for i,arg in enumerate(ctor.args):
                #    st.o.fl('__struct.%s = __arg_%d;', arg.ident, i)

                st.o.pl('obj = new Wrap(__struct);')
            
            st.o.pop('}')

        (st.o
         .fl('if( numParams > %d )', max(len(ctor.args) for ctor in ctors))
         .push('{')
         # TODO: build usage string
         .pl('md.throwException(t, "Bad arguments to constructor");')
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

        elif isinstance(ty, SemArrayType):
            ety = ty.elemType
            assert isinstance(ety, SemSymbolType), "nested arrays not supported"
            ident = ety.ident

            checkFn = None
            nativeType = ident

            if ident in BASIC_TYPES:
                if ident == 'ulong':
                    assert False, '%s: ulongs not supported' % ty.src

                if ident == 'bool':
                    checkFn = '&mdi.checkBoolParam'

                elif ident in ('byte', 'short', 'int', 'long',
                               'ubyte', 'ushort', 'uint'):
                    checkFn = '&mdi.checkIntParam(t, %r)'

                elif ident in ('float', 'double', 'real'):
                    checkFn = '&mdi.checkFloatParam'

                elif ident in ('char', 'wchar', 'dchar'):
                    checkFn = '&mdi.checkCharParam'

                elif ident == 'string':
                    checkFn = '&mdi.checkStringParam'
                    nativeType = 'char[]'

                elif ident == 'size_t':
                    checkFn = '&mdi.checkIntParam'

            else:
                checkFn = '&MD_%s.checkInstParam' % ident

            st.o.fl('mdi.MD_NativeArray.checkInstParamEx(t, %d, %s, typeid(%s));',
                    slot, checkFn, nativeType)
            

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
            return 'MD_%s.getValue(t, %d)' % (ident, slot)

        elif isinstance(ty, SemArrayType):
            ety = ty.elemType
            assert isinstance(ety, SemSymbolType), "nested arrays not supported"
            ident = ety.ident

            popFn = None
            nativeType = ety.ident

            if ident in BASIC_TYPES:
                if ident == 'ulong':
                    assert False, '%s: ulongs not supported' % ty.src
                    
                if ident == 'string':
                    nativeType = 'char[]'

                popFn = '&mdi.popPtr!(%s)' % nativeType

            else:
                popFn = '&MD_%s.popPtr' % nativeType

            return ('cast(%s[])(mdi.MD_NativeArray.popValueEx(t, %d, %s, typeid(%s)))'
                    % (nativeType, slot, popFn, nativeType))

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

                st.o.fl('mdi.MD_NativeArray.createFrom(t, %s);', value)

            elif est:
                st.o.fl('mdi.MD_NativeArray.createFrom(t, %s,'
                        +' &MD_%s.pushPtr);', value, ety.ident)

        else:
            st.o.fl('unimplemented/* type push %s, (%s) */;', ty, value)


    def generateInitMethodBinds(self, node, st):
        for decl in (d for d in node.decls
                     if isinstance(d, (SemFuncDecl, SemOpDecl,
                                       SemRoDecl, SemRwDecl))):
            if decl.ident == "this": continue

            if isinstance(decl, SemMixin):
                # do nothing
                pass

            elif isinstance(decl, SemOpDecl) or (
                    isinstance(decl, SemOverloadDecl)
                    and decl.type is SemOpDecl):
                d_name,md_name = self.getOpNames(decl)
                st.o.fl('c.method("%s", &op_method_%s);', md_name, decl.ident)

            else:
                st.o.fl('c.method("%s", &method_%s);', decl.ident, decl.ident)


    def getOpNames(self, node):
        ident = node.ident
        d_name = None
        md_name = None

        if ident in OP_SELF or (
                ident in OP_SELF_BIN
                or (ident.endswith("_r") and ident[:-2] in OP_SELF_BIN)
                or (ident.endswith("Assign") and ident[:-6] in OP_SELF_BIN)
            ):
            d_name = 'op' + ident[0].upper() + ident[1:]
            md_name = d_name

        elif ident in OP_MAP:
            d_name, md_name = OP_MAP[ident]

        elif ident in OP_SPECIAL:
            def missing(node,st):
                assert False, "missing special operator %s" % ident
            return getattr(self,"visitSemOpDecl_"+ident,missing)(node, st)

        else:
            assert False, "unknown operator %s" % ident

        return d_name, md_name


