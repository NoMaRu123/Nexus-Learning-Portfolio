import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Box,
  Button,
  Flex,
  Heading,
  Spinner,
  Tag,
  Text,
  Textarea,
  useToast,
  VStack,
} from "@chakra-ui/react";

import { getProjects, getEntries, createEntry } from "@/services/api";
import { useMode } from "@/context/ModeContext";
import { useAuth } from "@/context/AuthContext";
import type { Project, LearningEntry, PaginatedResponse } from "@/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 10;

const statusColor: Record<string, string> = {
  planning: "yellow",
  in_progress: "blue",
  completed: "green",
  archived: "gray",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Detail page for a single project.
 *
 * Displays project name, description, status, technology tags, and paginated
 * learning entries. In Tracker Mode an inline form allows adding new entries.
 *
 * **Validates: Requirements 6.2, 6.3, 6.4**
 */
export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const { isTrackerMode } = useMode();
  const { isAuthenticated } = useAuth();

  // ---- data state ----
  const [project, setProject] = useState<Project | null>(null);
  const [entries, setEntries] = useState<LearningEntry[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // ---- add-entry form state ----
  const [newDescription, setNewDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // ---- fetch project ----
  const fetchProject = useCallback(async () => {
    try {
      const allProjects = await getProjects();
      const match = allProjects.find((p) => p.id === id);
      if (!match) {
        setNotFound(true);
        return null;
      }
      setProject(match);
      return match;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load project";
      toast({
        title: "Error",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
      return null;
    }
  }, [id, toast]);

  // ---- fetch entries ----
  const fetchEntries = useCallback(
    async (pageNum: number) => {
      if (!id) return;
      try {
        const result: PaginatedResponse<LearningEntry> = await getEntries({
          project_id: id,
          page: pageNum,
          size: PAGE_SIZE,
        });
        setEntries(result.items);
        setTotalPages(result.total_pages);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load entries";
        toast({
          title: "Error",
          description: message,
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
    },
    [id, toast],
  );

  // ---- initial load ----
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      const found = await fetchProject();
      if (!cancelled && found) {
        await fetchEntries(1);
      }
      if (!cancelled) setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [fetchProject, fetchEntries]);

  // ---- page change ----
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    fetchEntries(newPage);
  };

  // ---- add entry ----
  const handleAddEntry = async () => {
    if (!newDescription.trim() || !id) return;
    setSubmitting(true);
    try {
      await createEntry({
        project_id: id,
        description: newDescription.trim(),
      });
      setNewDescription("");
      toast({ title: "Entry added", status: "success", duration: 3000 });
      // Refresh entries on current page
      await fetchEntries(page);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to add entry";
      toast({
        title: "Error",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSubmitting(false);
    }
  };

  // ---- render: loading ----
  if (loading) {
    return (
      <Flex justify="center" align="center" minH="60vh">
        <Spinner size="xl" thickness="4px" color="blue.500" />
      </Flex>
    );
  }

  // ---- render: not found ----
  if (notFound || !project) {
    return (
      <Box p={6}>
        <Button variant="link" onClick={() => navigate("/dashboard")} mb={4}>
          ← Back to Dashboard
        </Button>
        <Text color="gray.500" textAlign="center" mt={10}>
          Project not found.
        </Text>
      </Box>
    );
  }

  // ---- render: detail ----
  return (
    <Box p={6}>
      {/* Back navigation */}
      <Button variant="link" onClick={() => navigate("/dashboard")} mb={4}>
        ← Back to Dashboard
      </Button>

      {/* Project header */}
      <Heading as="h1" size="lg" mb={2}>
        {project.name}
      </Heading>

      {project.description && (
        <Text fontSize="md" color="gray.700" mb={2}>
          {project.description}
        </Text>
      )}

      <Flex align="center" gap={3} mb={2}>
        <Text fontSize="sm" color="gray.600">
          Status:
        </Text>
        <Tag
          size="md"
          colorScheme={statusColor[project.status] ?? "gray"}
        >
          {project.status}
        </Tag>
      </Flex>

      {project.technology_tags.length > 0 && (
        <Flex gap={2} flexWrap="wrap" mb={6}>
          {project.technology_tags.map((tag) => (
            <Tag key={tag} size="sm" colorScheme="blue" variant="subtle">
              {tag}
            </Tag>
          ))}
        </Flex>
      )}

      {/* Inline add-entry form (Tracker Mode only) */}
      {isTrackerMode && isAuthenticated && (
        <Box mb={6} p={4} borderWidth="1px" borderRadius="md">
          <Heading as="h3" size="sm" mb={2}>
            Add Learning Entry
          </Heading>
          <Textarea
            placeholder="Describe what you learned…"
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            mb={2}
            aria-label="New entry description"
          />
          <Button
            colorScheme="teal"
            size="sm"
            onClick={handleAddEntry}
            isLoading={submitting}
            isDisabled={!newDescription.trim()}
          >
            Submit
          </Button>
        </Box>
      )}

      {/* Learning entries */}
      <Heading as="h2" size="md" mb={4}>
        Learning Entries
      </Heading>

      {entries.length === 0 ? (
        <Text color="gray.500">No learning entries yet.</Text>
      ) : (
        <VStack spacing={3} align="stretch">
          {entries.map((entry) => (
            <Box
              key={entry.id}
              p={3}
              borderWidth="1px"
              borderRadius="md"
              bg="gray.50"
            >
              <Text fontSize="sm">{entry.description}</Text>
              <Text fontSize="xs" color="gray.500" mt={1}>
                {new Date(entry.timestamp).toLocaleString()}
              </Text>
            </Box>
          ))}
        </VStack>
      )}

      {/* Pagination controls */}
      {totalPages > 1 && (
        <Flex justify="center" align="center" gap={4} mt={6}>
          <Button
            size="sm"
            onClick={() => handlePageChange(page - 1)}
            isDisabled={page <= 1}
          >
            Previous
          </Button>
          <Text fontSize="sm">
            Page {page} of {totalPages}
          </Text>
          <Button
            size="sm"
            onClick={() => handlePageChange(page + 1)}
            isDisabled={page >= totalPages}
          >
            Next
          </Button>
        </Flex>
      )}
    </Box>
  );
}
