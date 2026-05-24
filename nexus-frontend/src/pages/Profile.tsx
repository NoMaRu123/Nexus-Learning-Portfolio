/**
 * Profile management page.
 *
 * Allows the authenticated user to view and edit their profile
 * (name, bio, contact email, social links) and upload a profile
 * picture with client-side cropping and compression.
 *
 * Requirements: 11.1, 11.4, 11.5, 11.6, 11.7, 11.13
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Avatar,
  Box,
  Button,
  Flex,
  FormControl,
  FormLabel,
  Heading,
  IconButton,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Spinner,
  Textarea,
  VStack,
  useDisclosure,
  useToast,
} from "@chakra-ui/react";
import Cropper from "react-easy-crop";
import type { Point } from "react-easy-crop";

import { getProfile, updateProfile, uploadPicture } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import type { UserProfile } from "@/types";
import type { Area } from "@/utils/imageUtils";
import { validateImageFile, getCroppedImg } from "@/utils/imageUtils";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ACCEPTED_IMAGE_TYPES = "image/jpeg,image/png,image/webp";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Profile() {
  const { user } = useAuth();
  const toast = useToast();

  // ---- profile data state ----
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // ---- form fields ----
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [socialLinks, setSocialLinks] = useState<{ key: string; value: string }[]>([]);

  // ---- image upload state ----
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [crop, setCrop] = useState<Point>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [uploading, setUploading] = useState(false);
  const { isOpen: isCropOpen, onOpen: onCropOpen, onClose: onCropClose } = useDisclosure();

  // ---- fetch profile on mount ----
  const fetchProfile = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getProfile();
      setProfile(data);
      setName(data.name ?? "");
      setBio(data.bio ?? "");
      setContactEmail(data.contact_email ?? "");

      // Convert social_links object to key-value array for editing
      const links = data.social_links ?? {};
      setSocialLinks(
        Object.entries(links).map(([key, value]) => ({ key, value })),
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load profile";
      toast({
        title: "Error loading profile",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  // ---- save profile ----
  const handleSave = async () => {
    setSaving(true);
    try {
      // Convert social links array back to object
      const linksObj: Record<string, string> = {};
      for (const link of socialLinks) {
        const trimmedKey = link.key.trim();
        if (trimmedKey) {
          linksObj[trimmedKey] = link.value.trim();
        }
      }

      const updated = await updateProfile({
        name: name || null,
        bio: bio || null,
        contact_email: contactEmail || null,
        social_links: Object.keys(linksObj).length > 0 ? linksObj : null,
      });

      setProfile(updated);
      toast({ title: "Profile updated", status: "success", duration: 3000 });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update profile";
      toast({
        title: "Error saving profile",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setSaving(false);
    }
  };

  // ---- social links helpers ----
  const addSocialLink = () => {
    setSocialLinks((prev) => [...prev, { key: "", value: "" }]);
  };

  const updateSocialLink = (index: number, field: "key" | "value", value: string) => {
    setSocialLinks((prev) =>
      prev.map((link, i) => (i === index ? { ...link, [field]: value } : link)),
    );
  };

  const removeSocialLink = (index: number) => {
    setSocialLinks((prev) => prev.filter((_, i) => i !== index));
  };

  // ---- image upload handlers ----
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input so the same file can be re-selected
    e.target.value = "";

    const validation = validateImageFile(file);
    if (!validation.valid) {
      toast({
        title: "Invalid file",
        description: validation.error,
        status: "warning",
        duration: 5000,
        isClosable: true,
      });
      return;
    }

    // Read file as data URL for the cropper
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      setImageSrc(reader.result as string);
      setCrop({ x: 0, y: 0 });
      setZoom(1);
      onCropOpen();
    });
    reader.readAsDataURL(file);
  };

  const onCropComplete = useCallback((_croppedArea: Area, croppedPixels: Area) => {
    setCroppedAreaPixels(croppedPixels);
  }, []);

  const handleCropConfirm = async () => {
    if (!imageSrc || !croppedAreaPixels) return;

    setUploading(true);
    try {
      const croppedBlob = await getCroppedImg(imageSrc, croppedAreaPixels);
      const updated = await uploadPicture(croppedBlob);
      setProfile(updated);
      toast({ title: "Profile picture updated", status: "success", duration: 3000 });
      onCropClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to upload picture";
      toast({
        title: "Upload error",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setUploading(false);
      setImageSrc(null);
    }
  };

  const handleCropCancel = () => {
    onCropClose();
    setImageSrc(null);
  };

  // ---- derive initials for placeholder avatar ----
  const initials = name
    ? name
        .split(" ")
        .map((part) => part[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.id.slice(0, 2).toUpperCase() ?? "?";

  // ---- render ----
  if (loading) {
    return (
      <Flex justify="center" align="center" minH="60vh">
        <Spinner size="xl" thickness="4px" color="blue.500" />
      </Flex>
    );
  }

  return (
    <Box p={6} maxW="600px" mx="auto">
      <Heading as="h1" size="lg" mb={6}>
        Profile
      </Heading>

      {/* ---- Profile picture section ---- */}
      <Flex direction="column" align="center" mb={8}>
        <Avatar
          size="2xl"
          name={name || undefined}
          src={profile?.picture_url ?? undefined}
          bg="gray.400"
          color="white"
          mb={3}
          aria-label="Profile picture"
        >
          {!profile?.picture_url && !name && initials}
        </Avatar>

        <Input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_IMAGE_TYPES}
          onChange={handleFileSelect}
          display="none"
          aria-label="Upload profile picture"
        />
        <Button
          size="sm"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
        >
          Change Picture
        </Button>
      </Flex>

      {/* ---- Profile form ---- */}
      <VStack spacing={4} align="stretch">
        <FormControl>
          <FormLabel>Name</FormLabel>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your full name"
          />
        </FormControl>

        <FormControl>
          <FormLabel>Bio</FormLabel>
          <Textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="Tell us about yourself…"
            rows={4}
          />
        </FormControl>

        <FormControl>
          <FormLabel>Contact Email</FormLabel>
          <Input
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </FormControl>

        {/* ---- Social links ---- */}
        <Box>
          <FormLabel>Social Links</FormLabel>
          <VStack spacing={2} align="stretch">
            {socialLinks.map((link, index) => (
              <Flex key={index} gap={2}>
                <Input
                  placeholder="Platform (e.g. GitHub)"
                  value={link.key}
                  onChange={(e) => updateSocialLink(index, "key", e.target.value)}
                  flex={1}
                />
                <Input
                  placeholder="URL"
                  value={link.value}
                  onChange={(e) => updateSocialLink(index, "value", e.target.value)}
                  flex={2}
                />
                <IconButton
                  aria-label="Remove social link"
                  icon={<span>✕</span>}
                  size="sm"
                  variant="ghost"
                  colorScheme="red"
                  onClick={() => removeSocialLink(index)}
                />
              </Flex>
            ))}
            <Button size="sm" variant="outline" onClick={addSocialLink}>
              + Add Link
            </Button>
          </VStack>
        </Box>

        <Button
          colorScheme="blue"
          onClick={handleSave}
          isLoading={saving}
          loadingText="Saving…"
          mt={2}
        >
          Save Profile
        </Button>
      </VStack>

      {/* ---- Crop modal ---- */}
      <Modal isOpen={isCropOpen} onClose={handleCropCancel} size="xl" isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Crop Profile Picture</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Box position="relative" w="100%" h="400px" bg="gray.900" borderRadius="md">
              {imageSrc && (
                <Cropper
                  image={imageSrc}
                  crop={crop}
                  zoom={zoom}
                  aspect={1}
                  onCropChange={setCrop}
                  onZoomChange={setZoom}
                  onCropComplete={onCropComplete}
                />
              )}
            </Box>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={handleCropCancel}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleCropConfirm}
              isLoading={uploading}
              loadingText="Uploading…"
            >
              Crop & Upload
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
