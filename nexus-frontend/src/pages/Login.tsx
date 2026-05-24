import { useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Heading,
  Input,
  Link,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";

import { useAuth } from "@/context/AuthContext";

/**
 * Login page with email/password form.
 *
 * On successful authentication the user is redirected to /dashboard.
 * Errors are surfaced via a Chakra UI toast.
 *
 * **Validates: Requirements 1.1, 1.2**
 */
export default function Login() {
  const navigate = useNavigate();
  const toast = useToast();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Login failed. Please try again.";
      toast({
        title: "Login failed",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box maxW="400px" mx="auto" mt={20} p={6}>
      <Heading as="h1" size="lg" mb={6} textAlign="center">
        Sign In
      </Heading>

      <form onSubmit={handleSubmit}>
        <VStack spacing={4}>
          <FormControl isRequired>
            <FormLabel>Email</FormLabel>
            <Input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </FormControl>

          <FormControl isRequired>
            <FormLabel>Password</FormLabel>
            <Input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </FormControl>

          <Button
            type="submit"
            colorScheme="teal"
            width="full"
            isLoading={loading}
          >
            Sign In
          </Button>
        </VStack>
      </form>

      <Text mt={4} textAlign="center" fontSize="sm">
        Don&apos;t have an account?{" "}
        <Link as={RouterLink} to="/register" color="teal.500">
          Register
        </Link>
      </Text>
    </Box>
  );
}
