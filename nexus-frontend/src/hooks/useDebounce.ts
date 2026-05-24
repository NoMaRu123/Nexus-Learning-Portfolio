import { useEffect, useState } from "react";

/**
 * Debounces a value by the specified delay in milliseconds.
 *
 * Returns the latest value only after `delay` ms have elapsed
 * since the last change, useful for search inputs to avoid
 * firing API calls on every keystroke.
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}
