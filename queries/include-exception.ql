import cpp

/**
 *
 * Finds if exception is included within the codebase
 *
 * The result of this query can enable flag NO_DISABLE_EXCEPTION_CATCHING in Emscripten
 *
 * More information according to Emscripten documentation:
 * Disabling Exception handling is on by default as the overhead of exceptions is quite high in size and speed currently.
 * In the future, wasm should improve that.
 * When exceptions are disabled, if an exception actually happens then it will not be caught and the program will halt.
 */

from PreprocessorDirective directive 

where directive.toString().matches("#include <exception>")

select directive
