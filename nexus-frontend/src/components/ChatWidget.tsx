import { useRef, useState } from "react";
import {
  Box,
  Button,
  Flex,
  IconButton,
  Input,
  Text,
  VStack,
  useDisclosure,
} from "@chakra-ui/react";

import { chatWithBot } from "@/services/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// ---------------------------------------------------------------------------
// Inline icon components (avoids @chakra-ui/icons dependency)
// ---------------------------------------------------------------------------

function ChatIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1.2em"
      height="1.2em"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="0.8em"
      height="0.8em"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Floating chat widget accessible on all pages.
 *
 * Renders a fixed-position button in the bottom-right corner that toggles
 * a chat panel. Maintains session history in component state and sends the
 * full history with each message for context continuity.
 *
 * **Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5**
 */
export default function ChatWidget() {
  const { isOpen, onToggle, onClose } = useDisclosure();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  /** Scroll to the latest message whenever the list updates. */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  /** Send the current input to the bot and append the response. */
  const handleSend = async () => {
    const query = inputValue.trim();
    if (!query || isLoading) return;

    const userMessage: ChatMessage = { role: "user", content: query };
    const updatedMessages = [...messages, userMessage];

    setMessages(updatedMessages);
    setInputValue("");
    setIsLoading(true);

    // Scroll after adding user message
    setTimeout(scrollToBottom, 50);

    try {
      const { response } = await chatWithBot(query, updatedMessages);
      const botMessage: ChatMessage = { role: "assistant", content: response };
      setMessages((prev) => [...prev, botMessage]);
    } catch {
      const errorMessage: ChatMessage = {
        role: "assistant",
        content:
          "Sorry, I'm having trouble responding right now. Please try again in a moment.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setTimeout(scrollToBottom, 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSend();
    }
  };

  return (
    <>
      {/* Floating toggle button */}
      {!isOpen && (
        <IconButton
          aria-label="Open chat"
          icon={<ChatIcon />}
          position="fixed"
          bottom={6}
          right={6}
          size="lg"
          colorScheme="blue"
          borderRadius="full"
          shadow="lg"
          onClick={onToggle}
          zIndex="popover"
        />
      )}

      {/* Chat panel */}
      {isOpen && (
        <Box
          position="fixed"
          bottom={6}
          right={6}
          width={{ base: "90vw", sm: "380px" }}
          maxH="500px"
          bg="white"
          borderRadius="lg"
          shadow="xl"
          border="1px solid"
          borderColor="gray.200"
          display="flex"
          flexDirection="column"
          zIndex="popover"
        >
          {/* Header */}
          <Flex
            px={4}
            py={3}
            bg="blue.500"
            color="white"
            borderTopRadius="lg"
            align="center"
            justify="space-between"
          >
            <Text fontWeight="bold" fontSize="sm">
              About Me Bot
            </Text>
            <IconButton
              aria-label="Close chat"
              icon={<CloseIcon />}
              size="xs"
              variant="ghost"
              color="white"
              _hover={{ bg: "blue.600" }}
              onClick={onClose}
            />
          </Flex>

          {/* Messages */}
          <VStack
            flex={1}
            overflowY="auto"
            px={4}
            py={3}
            spacing={3}
            align="stretch"
            maxH="350px"
          >
            {messages.length === 0 && !isLoading && (
              <Text fontSize="sm" color="gray.500" textAlign="center" py={4}>
                Ask me anything about the portfolio owner!
              </Text>
            )}

            {messages.map((msg, idx) => (
              <Flex
                key={idx}
                justify={msg.role === "user" ? "flex-end" : "flex-start"}
              >
                <Box
                  maxW="80%"
                  px={3}
                  py={2}
                  borderRadius="lg"
                  bg={msg.role === "user" ? "blue.500" : "gray.100"}
                  color={msg.role === "user" ? "white" : "gray.800"}
                  fontSize="sm"
                  whiteSpace="pre-wrap"
                  wordBreak="break-word"
                >
                  {msg.content}
                </Box>
              </Flex>
            ))}

            {/* Typing indicator */}
            {isLoading && (
              <Flex justify="flex-start">
                <Box
                  px={3}
                  py={2}
                  borderRadius="lg"
                  bg="gray.100"
                  fontSize="sm"
                  color="gray.500"
                >
                  Typing…
                </Box>
              </Flex>
            )}

            <div ref={messagesEndRef} />
          </VStack>

          {/* Input area */}
          <Flex px={3} py={2} borderTop="1px solid" borderColor="gray.200">
            <Input
              placeholder="Type a message…"
              size="sm"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              mr={2}
              isDisabled={isLoading}
              aria-label="Chat message input"
            />
            <Button
              size="sm"
              colorScheme="blue"
              onClick={handleSend}
              isLoading={isLoading}
              isDisabled={!inputValue.trim()}
            >
              Send
            </Button>
          </Flex>
        </Box>
      )}
    </>
  );
}
