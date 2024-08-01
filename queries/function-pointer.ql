import cpp

/**
 * 
 * Finds all expressions where a function pointer typedef is cast to another type.
 *
 * The result of this query can enable flag EMULATE_FUNCTION_POINTER_CASTS in Emscripten
 * 
 * More information according to Emscripten documentation:
 * Allows function pointers to be cast, wraps each call of an incorrect type with a runtime correction. 
 * This adds overhead and should not be used normally. Aside from making calls not fail, this tries to convert values as best it can.
 */

from Cast castexpr

where castexpr.getUnderlyingType() instanceof FunctionPointerType

select castexpr, castexpr.getLocation().getFile()
