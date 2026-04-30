export const extract_error = (error: any): string => {
  // Priority 1: Check for data.detail (singular)
  if (error?.data?.detail) {
    return String(error.data.detail);
  }

  // Priority 2: Check for data.details (plural) - for backward compatibility
  if (error?.data?.details) {
    return String(error.data.details);
  }

  // Priority 3: Check for .message
  if (error?.message) {
    return String(error.message);
  }

  // Priority 4: Check for data.message
  if (error?.data?.message) {
    return String(error.data.message);
  }

  // Priority 4: If error is an array, check first item recursively
  if (Array.isArray(error) && error.length > 0) {
    return extract_error(error[0]);
  }

  // Priority 5: If error is an object, check common error fields
  if (typeof error === "object" && error !== null) {
    // Check for common error field names
    if (error.details) return String(error.details);
    if (error.error) return extract_error(error.error);
    if (error.errors && Array.isArray(error.errors) && error.errors.length > 0) {
      return extract_error(error.errors[0]);
    }
  }

  // Fallback: Return error as string or default message
  if (error !== null && error !== undefined) {
    const errorString = String(error);
    // If it's not an empty string or just "[object Object]", return it
    if (errorString && errorString !== "[object Object]") {
      return errorString;
    }
  }

  return "Unknown error occurred";
};