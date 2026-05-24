import {
  Box,
  Card,
  CardBody,
  CloseButton,
  Flex,
  Heading,
  Tag,
  Text,
} from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";

import type { Skill } from "@/types";

// ---------------------------------------------------------------------------
// Proficiency → colour mapping
// ---------------------------------------------------------------------------

const proficiencyColor: Record<string, string> = {
  beginner: "green",
  intermediate: "blue",
  advanced: "orange",
  expert: "purple",
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SkillTileProps {
  skill: Skill;
  showControls: boolean;
  onDelete: (id: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Clickable card displaying a skill summary.
 *
 * Navigates to `/skills/:id` on click.
 * Optionally renders a delete button when `showControls` is true.
 *
 * **Validates: Requirements 5.2, 5.4**
 */
export default function SkillTile({ skill, showControls, onDelete }: SkillTileProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/skills/${skill.id}`);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(skill.id);
  };

  return (
    <Card
      variant="outline"
      cursor="pointer"
      onClick={handleClick}
      _hover={{ shadow: "md", borderColor: "blue.300" }}
      transition="box-shadow 0.2s, border-color 0.2s"
      role="link"
      aria-label={`View skill ${skill.name}`}
    >
      <CardBody>
        <Flex justify="space-between" align="start">
          <Box>
            <Heading as="h3" size="sm" mb={1}>
              {skill.name}
            </Heading>
            <Text fontSize="sm" color="gray.600">
              {skill.category}
            </Text>
            <Tag
              size="sm"
              mt={2}
              colorScheme={proficiencyColor[skill.proficiency_level] ?? "gray"}
            >
              {skill.proficiency_level}
            </Tag>
          </Box>
          {showControls && (
            <CloseButton
              aria-label={`Delete skill ${skill.name}`}
              size="sm"
              color="red.500"
              onClick={handleDelete}
            />
          )}
        </Flex>
      </CardBody>
    </Card>
  );
}
