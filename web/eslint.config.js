import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ignores: ["dist/**", "node_modules/**", "*.config.js"],
  },
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true, allowExportNames: ["useToast", "usePreferences"] },
      ],
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_" },
      ],
    },
  }
);
