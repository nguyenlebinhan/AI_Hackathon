
  # VADS - Prototype

  This is a code bundle for VADS - Prototype. The original project is available at https://www.figma.com/design/b7Egr7gD623CWdrn6JdVpK/VADS---Prototype.

  ## Running the code

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the development server. Vite proxies `/api` to
  `http://localhost:8000`, so the backend must be running locally.

  To use another backend, set `VITE_API_BASE_URL`, including the version prefix:

  ```dotenv
  VITE_API_BASE_URL=https://example.gov.vn/api/v1
  ```
