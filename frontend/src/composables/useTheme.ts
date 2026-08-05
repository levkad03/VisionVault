import { useDark, useToggle } from '@vueuse/core';

export function useTheme() {
  const isDark = useDark({
    selector: 'html',
    valueDark: 'dark',
    valueLight: '',
  });

  const toggleTheme = useToggle(isDark);

  return { isDark, toggleTheme };
}
