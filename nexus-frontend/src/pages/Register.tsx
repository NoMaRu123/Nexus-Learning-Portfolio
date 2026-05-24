import { useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Heading,
  Input,
  Link,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";

import { useAuth } from "@/context/AuthContext";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MIN_PASSWORD_LENGTH = 8;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Registration page with email/password form.
 *
 * Password must be at least 8 characters. On successful registration the
 * AuthContext auto-logs the user in and we redirect to /dashboard.
 *
 * **Validates: Requirements 1.1, 1.2**
 */
export default function Register() {
  const navigate = useNavigate();
  const toast = useToast();
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const isPasswordTooShort =
    password.length > 0 && password.length < MIN_PASSWORD_LENGTH;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password.length < MIN_PASSWORD_LENGTH) {
      toast({
        title: "Password too short",
        description: `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`,
        status: "warning",
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    setLoading(true);
    try {
      await register(email, password);
      navigate("/dashboard");
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Registration failed. Please try again.";
      toast({
        title: "Registration failed",
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
        Create Account
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

          <FormControl isRequired isInvalid={isPasswordTooShort}>
            <FormLabel>Password</FormLabel>
            <Input
              type="password"
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
            {isPasswordTooShort && (
              <FormErrorMessage>
                Password must be at least {MIN_PASSWORD_LENGTH} characters.
              </FormErrorMessage>
            )}
          </FormControl>

          <Button
            type="submit"
            colorScheme="teal"
            width="full"
            isLoading={loading}
            isDisabled={isPasswordTooShort}
          >
            Register
          </Button>
        </VStack>
      </form>

      <Text mt={4} textAlign="center" fontSize="sm">
        Already have an account?{" "}
        <Link as={RouterLink} to="/login" color="teal.500">
          Sign in
        </Link>
      </Text>
    </Box>
  );
}
