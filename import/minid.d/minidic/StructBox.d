/**
 * Contains a class for wrapping a struct.
 *
 * Authors: Daniel Keep <daniel.keep@gmail.com>
 * Copyright: See LICENSE.
 */
module minidic.StructBox;

/**
 * Wraps a struct in an object.  This is so that structs can be stored in
 * MiniD native objects.
 *
 * The struct is stored inside the object; as such, it shouldn't be used to
 * store pointers to structures.
 */
class StructBox(Struct)
{
    ///
    Struct value;

    ///
    this()
    {
    }

    ///
    this(ref Struct value)
    {
        this.value = value;
    }
}

