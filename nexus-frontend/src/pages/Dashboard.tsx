import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Flex,
  Heading,
  Input,
  Select,
  SimpleGrid,
  Spinner,
  Text,
  useToast,
} from "@chakra-ui/react";

import {
  getSkills,
  getProjects,
  getPublicProfile,
  createSkill,
  deleteSkill,
  createProject,
  deleteProject,
} from "@/services/api";
import { useMode } from "@/context/ModeContext";
import { useAuth } from "@/context/AuthContext";
import { useDebounce } from "@/hooks/useDebounce";
import SkillTile from "@/components/SkillTile";
import ProjectTile from "@/components/ProjectTile";
import PortfolioHeader from "@/components/PortfolioHeader";
import type { Skill, Project, PublicProfile } from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Union type so we can render skills and projects in a single grid. */
type TileItem =
  | { kind: "skill"; data: Skill }
  | { kind: "project"; data: Project };

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const { isTrackerMode, isPortfolioMode } = useMode();
  const { isAuthenticated } = useAuth();
  const toast = useToast();

  // ---- data state ----
  const [skills, setSkills] = useState<Skill[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [publicProfile, setPublicProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // ---- filter state ----
  const [searchText, setSearchText] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const debouncedSearch = useDebounce(searchText, 300);

  // ---- fetch on mount ----
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [fetchedSkills, fetchedProjects] = await Promise.all([
        getSkills(),
        getProjects(),
      ]);
      setSkills(fetchedSkills);
      setProjects(fetchedProjects);

      // In Portfolio Mode, fetch the public profile for the header
      if (isPortfolioMode) {
        try {
          const profile = await getPublicProfile();
          setPublicProfile(profile);
        } catch {
          // Profile fetch is best-effort; don't block the dashboard
          setPublicProfile(null);
        }
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load data";
      toast({
        title: "Error loading dashboard",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  }, [toast, isPortfolioMode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ---- derived: unique categories from skills ----
  const categories = useMemo(() => {
    const unique = new Set(skills.map((s) => s.category));
    return Array.from(unique).sort();
  }, [skills]);

  // ---- derived: filtered tile items ----
  const filteredItems = useMemo<TileItem[]>(() => {
    const query = debouncedSearch.toLowerCase();

    const matchedSkills: TileItem[] = skills
      .filter((s) => {
        const matchesSearch = query
          ? s.name.toLowerCase().includes(query)
          : true;
        const matchesCategory = selectedCategory
          ? s.category === selectedCategory
          : true;
        return matchesSearch && matchesCategory;
      })
      .map((s) => ({ kind: "skill" as const, data: s }));

    const matchedProjects: TileItem[] = projects
      .filter((p) => {
        const matchesSearch = query
          ? p.name.toLowerCase().includes(query)
          : true;
        // Projects don't have a category field — only filter by search
        return matchesSearch;
      })
      .map((p) => ({ kind: "project" as const, data: p }));

    return [...matchedSkills, ...matchedProjects];
  }, [skills, projects, debouncedSearch, selectedCategory]);

  // ---- CRUD handlers ----
  const handleAddSkill = async () => {
    const name = window.prompt("Skill name:");
    if (!name) return;
    const category = window.prompt("Category:") ?? "General";
    try {
      const created = await createSkill({ name, category });
      setSkills((prev) => [...prev, created]);
      toast({ title: "Skill created", status: "success", duration: 3000 });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to create skill";
      toast({ title: "Error", description: message, status: "error", duration: 5000, isClosable: true });
    }
  };

  const handleDeleteSkill = async (id: string) => {
    try {
      await deleteSkill(id);
      setSkills((prev) => prev.filter((s) => s.id !== id));
      toast({ title: "Skill deleted", status: "info", duration: 3000 });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to delete skill";
      toast({ title: "Error", description: message, status: "error", duration: 5000, isClosable: true });
    }
  };

  const handleAddProject = async () => {
    const name = window.prompt("Project name:");
    if (!name) return;
    const description = window.prompt("Description:") ?? "";
    try {
      const created = await createProject({ name, description });
      setProjects((prev) => [...prev, created]);
      toast({ title: "Project created", status: "success", duration: 3000 });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to create project";
      toast({ title: "Error", description: message, status: "error", duration: 5000, isClosable: true });
    }
  };

  const handleDeleteProject = async (id: string) => {
    try {
      await deleteProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
      toast({ title: "Project deleted", status: "info", duration: 3000 });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to delete project";
      toast({ title: "Error", description: message, status: "error", duration: 5000, isClosable: true });
    }
  };

  // ---- render ----
  if (loading) {
    return (
      <Flex justify="center" align="center" minH="60vh">
        <Spinner size="xl" thickness="4px" color="blue.500" />
      </Flex>
    );
  }

  return (
    <Box p={6}>
      <Heading as="h1" size="lg" mb={6}>
        Dashboard
      </Heading>

      {/* ---- Portfolio Mode: public profile header ---- */}
      {isPortfolioMode && publicProfile && (
        <PortfolioHeader profile={publicProfile} />
      )}

      {/* ---- Toolbar: search, filter, add buttons ---- */}
      <Flex
        direction={{ base: "column", md: "row" }}
        gap={4}
        mb={6}
        align={{ md: "center" }}
      >
        <Input
          placeholder="Search by name…"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          maxW={{ md: "300px" }}
          aria-label="Search tiles by name"
        />

        <Select
          placeholder="All categories"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          maxW={{ md: "220px" }}
          aria-label="Filter by category"
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </Select>

        {isTrackerMode && isAuthenticated && (
          <>
            <Button colorScheme="teal" onClick={handleAddSkill}>
              Add Skill
            </Button>
            <Button colorScheme="purple" onClick={handleAddProject}>
              Add Project
            </Button>
          </>
        )}
      </Flex>

      {/* ---- Tile grid ---- */}
      {filteredItems.length === 0 ? (
        <Text color="gray.500" textAlign="center" mt={10}>
          No skills or projects found.
        </Text>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={5}>
          {filteredItems.map((item) =>
            item.kind === "skill" ? (
              <SkillTile
                key={`skill-${item.data.id}`}
                skill={item.data}
                showControls={isTrackerMode && isAuthenticated}
                onDelete={handleDeleteSkill}
              />
            ) : (
              <ProjectTile
                key={`project-${item.data.id}`}
                project={item.data}
                showControls={isTrackerMode && isAuthenticated}
                onDelete={handleDeleteProject}
              />
            ),
          )}
        </SimpleGrid>
      )}
    </Box>
  );
}
