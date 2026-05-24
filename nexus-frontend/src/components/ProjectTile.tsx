import {
  Box,
  Card,
  CardBody,
  CloseButton,
  Flex,
  Heading,
  Tag,
} from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";

import type { Project } from "@/types";

// ---------------------------------------------------------------------------
// Status → colour mapping
// ---------------------------------------------------------------------------

const statusColor: Record<string, string> = {
  planning: "yellow",
  in_progress: "blue",
  completed: "green",
  archived: "gray",
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ProjectTileProps {
  project: Project;
  showControls: boolean;
  onDelete: (id: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Clickable card displaying a project summary.
 *
 * Navigates to `/projects/:id` on click.
 * Optionally renders a delete button when `showControls` is true.
 *
 * **Validates: Requirements 5.3, 5.4**
 */
export default function ProjectTile({ project, showControls, onDelete }: ProjectTileProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/projects/${project.id}`);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(project.id);
  };

  return (
    <Card
      variant="outline"
      cursor="pointer"
      onClick={handleClick}
      _hover={{ shadow: "md", borderColor: "purple.300" }}
      transition="box-shadow 0.2s, border-color 0.2s"
      role="link"
      aria-label={`View project ${project.name}`}
    >
      <CardBody>
        <Flex justify="space-between" align="start">
          <Box>
            <Heading as="h3" size="sm" mb={1}>
              {project.name}
            </Heading>
            <Tag
              size="sm"
              mt={1}
              colorScheme={statusColor[project.status] ?? "gray"}
            >
              {project.status}
            </Tag>
            {project.technology_tags.length > 0 && (
              <Flex gap={1} mt={2} flexWrap="wrap">
                {project.technology_tags.map((tag) => (
                  <Tag key={tag} size="sm" colorScheme="gray">
                    {tag}
                  </Tag>
                ))}
              </Flex>
            )}
          </Box>
          {showControls && (
            <CloseButton
              aria-label={`Delete project ${project.name}`}
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
