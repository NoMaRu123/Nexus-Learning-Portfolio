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

import { getSkills, getEntries, createEntry } from "@/services/api";
import { useMode } from "@/context/ModeContext";
import { useAuth } from "@/context/AuthContext";
import type { Skill, LearningEntry, PaginatedResponse } from "@/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 10;

const proficiencyColor: Record<string, string> = {
  beginner: "green",
  intermediate: "blue",
  advanced: "orange",
  expert: "purple",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Detail page for a single skill.
 *
 * Displays skill name, category, proficiency level, and paginated learning
 * entries. In Tracker Mode an inline form allows adding new entries.
 *
 * **Validates: Requirements 6.1, 6.3, 6.4**
 */
export default function SkillDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const { isTrackerMode } = useMode();
  const { isAuthenticated } = useAuth();

  // ---- data state ----
  const [skill, setSkill] = useState<Skill | null>(null);
  const [entries, setEntries] = useState<LearningEntry[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // ---- add-entry form state ----
  const [newDescription, setNewDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // ---- fetch skill ----
  const fetchSkill = useCallback(async () => {
    try {
      const allSkills = await getSkills();
      const match = allSkills.find((s) => s.id === id);
      if (!match) {
        setNotFound(true);
        return null;
      }
      setSkill(match);
      return match;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load skill";
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
          skill_id: id,
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
      const found = await fetchSkill();
      if (!cancelled && found) {
        await fetchEntries(1);
      }
      if (!cancelled) setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [fetchSkill, fetchEntries]);

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
      await createEntry({ skill_id: id, description: newDescription.trim() });
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
  if (notFound || !skill) {
    return (
      <Box p={6}>
        <Button variant="link" onClick={() => navigate("/dashboard")} mb={4}>
          ← Back to Dashboard
        </Button>
        <Text color="gray.500" textAlign="center" mt={10}>
          Skill not found.
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

      {/* Skill header */}
      <Heading as="h1" size="lg" mb={2}>
        {skill.name}
      </Heading>
      <Text fontSize="md" color="gray.600" mb={2}>
        Category: {skill.category}
      </Text>
      <Tag
        size="md"
        colorScheme={proficiencyColor[skill.proficiency_level] ?? "gray"}
        mb={6}
      >
        {skill.proficiency_level}
      </Tag>

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
