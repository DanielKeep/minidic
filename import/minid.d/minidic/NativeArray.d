/* Generated by minidic */
module minidic.NativeArray;

static import md = minid.api;
static import mdu = minid.utils;
static import mdi = minidic.binding;
import tango.util.Convert : to;

struct MD_Module
{
static:
  void init(md.MDThread* t)
  {
    MD_NativeArray.init(t);
    
    md.makeModule(t, "minidic.NativeArray", function md.uword(md.MDThread* t, md.uword numParams)
    {
      MD_NativeArray.initModule(t);
      return 0;
    });
  }
}


// This is imported automatically.
//import tango.util.Convert : to;

/*
 * This is our actual payload.
 */

private class NativeArray
{
    /// This is the untyped slice of memory we're wrapping.
    void[] data;
    /**
        ti is used to determine how long individual elements are.  Also used
        to tell scripts what type the array elements are (if they're
        interested).
    */
    TypeInfo ti;
    /// Function used to push an element to the MiniD stack via a pointer.
    void function(md.MDThread* t, void* ptr) pushElement;
}

struct MD_NativeArray
{
static:
  const Name = "NativeArray";
  const FQName = "minidic.NativeArray.NativeArray";
  
  /// Reference to the MiniD class
  ulong classRef = ulong.max;
  
  enum : bool { WrapStruct = false }
  alias NativeArray RawWrapRef;
  alias NativeArray Wrap;
  
  void init(md.MDThread* t)
  {
    md.CreateClass(t, FQName, (md.CreateClass* c)
    {
      c.method("constructor", &constructor);
      c.method("opIndex", &op_method_index);
      c.method("opSlice", &op_method_slice);
      c.method("opLength", &method_opLength);
      c.method("opApply", &method_opApply);
      c.method("toArray", &method_toArray);
      c.method("elemType", &method_elemType);
    });
    
    md.newFunction(t, &allocator, "allocator");
    md.setAllocator(t, -2);
    
    classRef = md.createRef(t, -1);
    assert( classRef != classRef.max );
    
    md.newGlobal(t, Name);
  }
  
  void initModule(md.MDThread* t)
  {
    if( classRef == classRef.max )
      init(t);
    
    md.pushRef(t, classRef);
    md.newGlobal(t, Name);
  }
  
  void checkInstParam(md.MDThread* t, md.word slot = 0)
  {
    mdi.checkInstParamRef(t, slot, classRef);
  }
  
  Wrap getWrap(md.MDThread* t, md.word slot = 0)
  {
    Object r = null;
    md.stackCheck(t,
    {
      md.getExtraVal(t, slot, 0);
      if( !md.isNull(t, -1) )
        r = md.getNativeObj(t, -1);
      md.pop(t);
    });
    return cast(Wrap) r;
  }
  
  void setWrap(md.MDThread* t, Wrap obj, md.word slot = 0)
  {
    md.stackCheck(t,
    {
      md.pushNativeObj(t, obj);
      md.setExtraVal(t, slot<0?slot-1:slot, 0);
    });
  }
  
  NativeArray getValue(md.MDThread* t, md.word slot = 0)
  {
    auto wrap = getWrap(t, slot);
    return wrap;
  }
  
  void pushPtr(md.MDThread* t, void* ptr)
  {
    create(t, cast(RawWrapRef)(*cast(Object*) ptr));
  }
  
  NativeArray popValue(md.MDThread* t)
  {
    auto r = getWrap(t, -1);
    md.pop(t);
    
    return r;
  }
  
  void popPtr(md.MDThread* t, void* ptr)
  {
    *(cast(RawWrapRef*)(ptr)) = popValue(t);
  }
  
  void create(md.MDThread* t, md.word slot = 0)
  {
    create(t, slot, null, true);
  }
  
  void create(md.MDThread* t, RawWrapRef obj)
  {
    assert( classRef != classRef.max, "classRef for "~FQName~" hasn't been set" );
    auto slot = md.pushRef(t, classRef);
    create(t, slot, obj, false);
    md.swap(t);
    md.pop(t);
  }
  
  void create(md.MDThread* t, md.word slot, RawWrapRef obj, bool hasArgs)
  {
    md.newInstance(t, slot, 1, 0);
    md.stackCheck(t,
    {
      if( obj !is null )
      {
        md.pushNativeObj(t, obj);
        md.setExtraVal(t, -2, 0);
      }
    });
    
    md.dup(t);
    md.pushNull(t);
    
    if( hasArgs )
    {
      md.rotateAll(t, 3);
      md.methodCall(t, 2, "constructor", 0);
    }
    else
    {
      md.methodCall(t, -2, "constructor", 0);
    }
    
    md.stackCheck(t,
    {
      md.getExtraVal(t, -1, 0);
      assert( md.getNativeObj(t, -1) !is null );
      md.pop(t);
    });
  }
  
  md.uword allocator(md.MDThread* t, md.uword numParams)
  {
    create(t, 0);
    return 1;
  }
  
  md.uword constructor(md.MDThread* t, md.uword numParams)
  {
    mdi.checkInstParamRef(t, 0, classRef);
    auto obj = getWrap(t);
    
    if( obj is null )
    {
      md.stackCheck(t, delegate void()
      {
        if( obj is null )
        {
          md.throwException(t, "Cannot create NativeArray objects");
          assert(false);
        }
      });
      assert( obj !is null, "NativeArray constructor didn't initialise an object" );
      setWrap(t, obj);
    }
    
    return 0;
  }
  

    /**
        Creates a new NativeArray on the stack from the given array.

        You can also optionally specify a push function.  A push function will
        be automatically supplied if the elements are integers, floats or
        strings.
    */
    static void createFrom(T)(md.MDThread* t, T[] arr)
    {
        void function(md.MDThread*, void*) pushFn;

        static if( is( T : bool ) )
        {
            pushFn = function void(md.MDThread* t, void* ptr)
            {
                auto v = *cast(T*)ptr;
                md.pushBool(t, v);
            };
        }
        else static if( is( T : dchar ) )
        {
            pushFn = function void(md.MDThread* t, void* ptr)
            {
                auto v = *cast(T*)ptr;
                md.pushChar(t, v);
            };
        }
        else static if( is( T : long ) )
        {
            pushFn = function void(md.MDThread* t, void* ptr)
            {
                auto v = *cast(T*)ptr;
                md.pushInt(t, v);
            };
        }
        else static if( is( T : real ) )
        {
            pushFn = function void(md.MDThread* t, void* ptr)
            {
                auto v = *cast(T*)ptr;
                md.pushFloat(t, v);
            };
        }
        else static if( is( T : char[] ) )
        {
            pushFn = function void(md.MDThread* t, void* ptr)
            {
                auto v = *cast(T*)ptr;
                md.pushString(t, v);
            };
        }
        else
        {
            pragma(msg, "Error: NativeArray: I don't know how to wrap a "
                    ~ T.stringof ~ "[]");
            static assert(false);
        }

        MD_NativeArray.createFrom(t, arr, pushFn);
    }

    /// ditto
    static void createFrom(T,U=void)(md.MDThread* t, T[] arr,
            void function(md.MDThread*, void*) pushFn)
    {
        auto obj = new NativeArray;
        obj.data = arr;
        obj.ti = typeid(T);
        obj.pushElement = pushFn;

        create(t, obj);
    }

    /*
        opApply iterator function.
    */
    static md.uword opApply_iter(md.MDThread* t, md.uword numParams)
    {
        md.checkInstParam(t, 0);
        auto obj = getWrap(t);

        if( md.isNull(t, 1) )
        {
            if( obj.data.length == 0 )
            {
                md.pushNull(t);
                md.pushNull(t);
            }
            else
            {
                md.pushInt(t, 0);
                obj.pushElement(t, obj.data.ptr);
            }
            return 2;
        }
        else
        {
            auto idx = md.checkIntParam(t, 1);
            ++ idx;
            auto tsize = obj.ti.tsize;
            auto len = obj.data.length / tsize;
            if( idx >= len )
            {
                md.pushNull(t);
                md.pushNull(t);
            }
            else
            {
                md.pushInt(t, idx);
                obj.pushElement(t, obj.data.ptr + idx*tsize);
            }
            return 2;
        }
    }

    static void checkInstParamEx(md.MDThread* t, md.word slot,
            void function(md.MDThread*, md.word) checkFn,
            TypeInfo elemTi)
    {
        auto index = md.absIndex(t, slot);

        // TODO: verify all elements of minid arrays
        if( ! (isInstParamRef(t, slot) || md.isArray(t, slot)) )
        {
            md.pushTypeString(t, index);

            if( index == 0 )
                md.throwException(t, "Expected array for 'this', not {}",
                        md.getString(t, -1));

            else
                md.throwException(t, "Expected array for parameter {},"
                        " not {}", index, md.getString(t, -1));

            assert(false);
        }
    }

    static bool isInstParamRef(md.MDThread* t, md.word slot)
    {
        auto index = md.absIndex(t, slot);
        if( ! md.isInstance(t, index) )
            return false;

        md.pushRef(t, classRef);
        auto r = md.as(t, index, -1);
        md.pop(t);
        return r;
    }

    /**
        This will take an array (either a NativeArray or a MiniD array) off
        the top of the MiniD stack, convert it to a D array and return it as a
        void[] to be casted back to the original type by the caller.
    */
    static void[] popValueEx(md.MDThread* t, md.word slot,
            void function(md.MDThread*, void*) popFn,
            TypeInfo elemTi)
    {
        if( isInstParamRef(t, -1) )
            return popValueNative(t, slot, elemTi);
        
        else if( md.isArray(t, -1) )
            return popValueMiniD(t, slot, popFn, elemTi);

        else
        {
            md.pushTypeString(t, -1);
            md.throwException(t, "Expected array, not {}",
                    md.getString(t, -1));
            assert(false);
        }
    }

    static void[] popValueNative(md.MDThread* t, md.word slot, TypeInfo elemTi)
    {
        md.checkInstParam(t, slot);
        auto obj = getWrap(t);

        // BUG: this will fail for shared libraries, but we don't have much
        // choice given that Walter has never fucking fixed TypeInfo.
        if( obj.ti !is elemTi )
        {
            md.throwException(t, "Incompatible native array types; "
                    "needed '{}', got '{}'", elemTi.toString,
                    obj.ti.toString);
            assert(false);
        }

        return obj.data;
    }

    static void[] popValueMiniD(md.MDThread* t, md.word slot,
            void function(md.MDThread*, void*) popFn,
            TypeInfo elemTi)
    {
        auto index = md.absIndex(t, slot);

        if( !md.isArray(t, index) )
        {
            md.pushTypeString(t, index);
            md.throwException(t, "Expected array, not {}", md.getString(t, -1));
            assert(false);
        }

        auto l = md.len(t, index);

        if( l == 0 )
            return null;

        if( to!(size_t)(l) > size_t.max )
        {
            md.throwException(t, "Array too large");
            assert(false);
        }

        // TODO: tell the GC whether there are pointers or not.
        // HACK: should use ubyte's and specify pointer presence.
        auto r = cast(ubyte[])(new void*[]((elemTi.tsize*l+1)/size_t.sizeof));
        scope(failure) delete r;

        for( size_t i=0 ; i<l ; ++i )
        {
            md.idxi(t, index, i);
            popFn(t, r.ptr + i*elemTi.tsize);
        }

        return r;
    }
      
  md.uword op_method_index(md.MDThread* t, md.uword numParams)
  {
    mdi.checkInstParamRef(t, 0, classRef);
    auto obj = getWrap(t);
    
    {

        auto i = to!(size_t)(md.checkIntParam(t, 1));
        if( i >= obj.data.length / obj.ti.tsize )
        {
            md.throwException(t, "index '{}' out of bounds", i);
            assert(false);
        }
        md.stackCheck(t, 1,
        {
            obj.pushElement(t, obj.data.ptr + i*obj.ti.tsize);
        });
        return 1;
          
    }
    md.throwException(t, "Bad arguments to index");
    assert(false);
  }
  
  md.uword op_method_slice(md.MDThread* t, md.uword numParams)
  {
    mdi.checkInstParamRef(t, 0, classRef);
    auto obj = getWrap(t);
    
    {

        auto i = to!(size_t)(md.checkIntParam(t, 1));
        auto j = to!(size_t)(md.checkIntParam(t, 2));

        auto tsize = obj.ti.tsize;
        auto len = obj.data.length / tsize;

        if( i >= len || j > len )
        {
            md.throwException(t, "slice '{}..{}' out of bounds", i, j);
            assert(false);
        }
        if( i > j )
        {
            md.throwException(t, "your slice indices are backwards");
            assert(false);
        }
        if( i == j )
        {
            md.newArray(t, 0);
            return 1;
        }

        for( auto off = i ; off < j ; ++off )
        {
            md.stackCheck(t, 1,
            {
                obj.pushElement(t, obj.data.ptr + off*obj.ti.tsize);
            });
        }

        md.newArrayFromStack(t, j-i);
        return 1;
          
    }
    md.throwException(t, "Bad arguments to slice");
    assert(false);
  }
  
  md.uword method_opLength(md.MDThread* t, md.uword numParams)
  {
    mdi.checkInstParamRef(t, 0, classRef);
    auto obj = getWrap(t);
    
    {

        md.pushInt(t, obj.data.length / obj.ti.tsize);
        return 1;
          
    }
    md.throwException(t, "Bad arguments to opLength");
    assert(false);
  }
  
  md.uword method_opApply(md.MDThread* t, md.uword numParams)
  {
    mdi.checkInstParamRef(t, 0, classRef);
    auto obj = getWrap(t);
    
    {

        md.newFunction(t, &opApply_iter, "opApply_iter");
        md.dup(t, 0);
        md.pushNull(t);
        return 3;
          
    }
    md.throwException(t, "Bad arguments to opApply");
    assert(false);
  }
  
  md.uword method_toArray(md.MDThread* t, md.uword numParams)
  {
    mdi.checkInstParamRef(t, 0, classRef);
    auto obj = getWrap(t);
    
    {

        if( obj.data.length == 0 )
        {
            md.newArray(t, 0);
            return 1;
        }

        auto len = obj.data.length / obj.ti.tsize;
        for( size_t i = 0 ; i < len ; ++i )
        {
            md.stackCheck(t, 1,
            {
                obj.pushElement(t, obj.data.ptr + i*obj.ti.tsize);
            });
        }

        md.newArrayFromStack(t, len);
        return 1;
          
    }
    md.throwException(t, "Bad arguments to toArray");
    assert(false);
  }
  
  md.uword method_elemType(md.MDThread* t, md.uword numParams)
  {
    mdi.checkInstParamRef(t, 0, classRef);
    auto obj = getWrap(t);
    
    {

        md.pushString(t, obj.ti.toString);
        return 1;
          
    }
    md.throwException(t, "Bad arguments to elemType");
    assert(false);
  }
  
}

