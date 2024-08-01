import cpp

/**
 *
 * Finds all threads defined within the codebase
 *
 * The result of this query can enable flag -pthread in Emscripten
 *
 * More information according to Emscripten documentation:
 * By default, support for pthreads is not enabled. To enable code generation for pthreads, the following command line flags exist:
 * Pass the compiler flag -pthread when compiling any .c/.cpp files, and when linking to generate the final output .js file.
 */

from Variable var

where var.getType().toString().matches("%std::thread%") or var.getType().toString().matches("%pthread_t%")

select var, var.getName(), var.getLocation().getFile()
