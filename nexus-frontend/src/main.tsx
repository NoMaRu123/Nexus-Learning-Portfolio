import React from "react";
import ReactDOM from "react-dom/client";
import { ChakraProvider } from "@chakra-ui/react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { ModeProvider } from "@/context/ModeContext";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ChakraProvider>
      <BrowserRouter>
        <ModeProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </ModeProvider>
      </BrowserRouter>
    </ChakraProvider>
  </React.StrictMode>,
);
