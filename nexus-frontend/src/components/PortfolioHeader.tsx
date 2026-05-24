import {
  Avatar,
  Box,
  Flex,
  Heading,
  HStack,
  Link,
  Text,
  VStack,
} from "@chakra-ui/react";

import type { PublicProfile } from "@/types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PortfolioHeaderProps {
  /** Public profile data for the portfolio owner. */
  profile: PublicProfile;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Displays the portfolio owner's public profile information.
 *
 * Rendered at the top of the Dashboard in Portfolio Mode so visitors
 * can see the owner's name, bio, contact email, social links, and
 * profile picture.
 *
 * **Validates: Requirements 14.3**
 */
export default function PortfolioHeader({ profile }: PortfolioHeaderProps) {
  const { name, bio, contact_email, social_links, picture_url } = profile;

  return (
    <Box
      bg="white"
      borderRadius="lg"
      boxShadow="sm"
      p={6}
      mb={8}
      borderWidth="1px"
      borderColor="gray.200"
    >
      <Flex
        direction={{ base: "column", md: "row" }}
        align={{ base: "center", md: "flex-start" }}
        gap={6}
      >
        {/* Profile picture or placeholder avatar */}
        <Avatar
          size="2xl"
          name={name ?? "Portfolio Owner"}
          src={picture_url ?? undefined}
          aria-label={
            name
              ? `Profile picture of ${name}`
              : "Portfolio owner profile picture"
          }
        />

        {/* Profile details */}
        <VStack align={{ base: "center", md: "flex-start" }} spacing={2} flex={1}>
          <Heading as="h2" size="lg">
            {name ?? "Portfolio Owner"}
          </Heading>

          {bio && (
            <Text color="gray.600" fontSize="md" whiteSpace="pre-line">
              {bio}
            </Text>
          )}

          {contact_email && (
            <Text fontSize="sm" color="gray.500">
              <Link href={`mailto:${contact_email}`} color="blue.500">
                {contact_email}
              </Link>
            </Text>
          )}

          {social_links && Object.keys(social_links).length > 0 && (
            <HStack spacing={4} pt={1} wrap="wrap">
              {Object.entries(social_links).map(([platform, url]) => (
                <Link
                  key={platform}
                  href={url}
                  color="blue.500"
                  fontSize="sm"
                  isExternal
                >
                  {platform}
                </Link>
              ))}
            </HStack>
          )}
        </VStack>
      </Flex>
    </Box>
  );
}
