import cpp

/**
 *
 * Finds if pthread.h is included within the codebase
 *
 * The result of this query can enable flag -pthread in Emscripten
 *
 * More information according to Emscripten documentation:
 * By default, support for pthreads is not enabled. To enable code generation for pthreads, the following command line flags exist:
 * Pass the compiler flag -pthread when compiling any .c/.cpp files, and when linking to generate the final output .js file.
 */

from PreprocessorDirective directive

where directive.toString().matches("#include <pthread.h>")

select directive
