import cpp

/**
 *
 * Finds all variables with the type long double.
 *
 * The result of this query can enable flag PRINTF_LONG_DOUBLE in Emscripten
 *
 * More information according to Emscripten documentation:
 * While LLVM's wasm32 has long double = float128, we don't support printing that at full precision by default.
 * Instead we print as 64-bit doubles, which saves libc code size.
 * You can flip this option on to get a libc with full long double printing precision.
 */

from Variable var

where var.getType().getUnspecifiedType().getName() = "long double"

select var, var.getName(), var.getLocation().getFile()
