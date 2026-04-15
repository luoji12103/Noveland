import nextVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
  {
    ignores: [".next/**", "node_modules/**", "coverage/**", "playwright-report/**", "test-results/**"],
  },
  ...nextVitals,
];

export default eslintConfig;
