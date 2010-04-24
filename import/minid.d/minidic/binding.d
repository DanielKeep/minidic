module minidic.binding;

import md = minid.api;

public import minidic.NativeArray : MD_NativeArray;
public import minidic.StructBox : StructBox;

/**
    Checks that the parameter at the given index is an instance of the class
    given by reference.

    Params:
        slot    = The stack slot of the parameter to check.
        classRef= Reference to the class object.
*/

void checkInstParamRef(md.MDThread* t, md.word slot, ulong classRef)
{
    auto index = md.absIndex(t, slot);
    md.checkInstParam(t, index);

    md.pushRef(t, classRef);

    if( !md.as(t, index, -1) )
    {
        auto name = md.className(t, -1);
        md.pushTypeString(t, index);

        if( index == 0 )
            md.throwException(t, "Expected instance of class {} "
                    "for 'this', not {}", name, getString(t, -1));

        else
            md.throwException(t, "Expected instance of class {} "
                    "for parameter {}, not {}",
                    name, index, getString(t, -1));
    }

    md.pop(t);
}

/**
    popPtr implementation for basic MiniD types.
*/

void popPtr!(T)(MDThread* t, void* ptr)
{
    static if( is( T : bool ) )
    {
        *cast(T*)ptr = md.checkBoolParam(t, -1);
    }
    else static if( is( T : long ) )
    {
        *cast(T*)ptr = to!(T)(md.checkIntParam(t, -1));
    }
    else static if( is( T : dchar ) )
    {
        *cast(T*)ptr = to!(T)(md.checkCharParam(t, -1));
    }
    else static if( is( T : real ) )
    {
        *cast(T*)ptr = to!(T)(md.checkFloatParam(t, -1));
    }
    else static if( is( T == char[] ) )
    {
        *cast(T*)ptr = md.checkStringParam(t, -1);
    }
    else
        static assert(false, "cannot pop type "~T.stringof);
}

/**
    Checks that the parameter at the given index is a function.
*/
void checkFunctionParam(md.MDThread* t, word slot)
{
    auto index = md.absIndex(t, slot);

    if( !md.isFunction(t, index) )
    {
        md.pushTypeString(t, index);

        if( index == 0 )
            md.throwException(t, "Expected function for 'this', not {}",
                    getString(t, -1));

        else
            md.throwException(t, "Expected function for parameter {}, not {}",
                    index, getString(t, -1));
    }
}

