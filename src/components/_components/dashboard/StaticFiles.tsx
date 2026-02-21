"use client";

import React, { useState } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Locale } from "../../../../i18n.config";
import { fetchData } from "@/lib/api/fetchData";
import { postFormData } from "@/lib/api/postFormData";
import { putData } from "@/lib/api/putApi";
import { patchData } from "@/lib/api/patchApi";
import { deleteData } from "@/lib/api/deleteApi";
import { toast } from "react-toastify";
import { Button } from "@/components/ui/button";
import IsLoading from "../ISloading";
import GlobalModal from "../GlobalModal";
import { extract_error } from "@/lib/api/errorApi";
import { FaEdit, FaTrash, FaPlus, FaCheckCircle, FaTimesCircle, FaFilePdf, FaDownload } from "react-icons/fa";
import Pagination from "../Pagination";
import { FILE_TYPES } from "@/lib/constants/fileTypes";

type InstructionFile = {
  id: number;
  file_type: string;
  file_type_display: string;
  title: string;
  file: string;
  file_url: string;
  description: string;
  is_active: boolean;
  version: number;
  created_by: number;
  created_by_email: string;
  updated_by: number;
  updated_by_email: string;
  created_at: string;
  updated_at: string;
};

type InstructionFilesResponse = {
  success: boolean;
  data: {
    instruction_files: InstructionFile[];
    pagination: {
      count: number;
      num_pages: number;
      current_page: number;
      page_size: number;
    };
  };
};

type StaticFilesFormData = {
  file_type: string;
  title: string;
  file: FileList;
  description: string;
  is_active: string;
};

type StaticFilesProps = {
  trans: any;
  token?: string;
  locale: Locale;
};

export default function StaticFiles({
  trans,
  token,
  locale,
}: StaticFilesProps) {
  const [page, setPage] = useState(1);
  const [showFormModal, setShowFormModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<InstructionFile | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [filters, setFilters] = useState({
    is_active: "true",
    file_type: "",
  });
  const queryClient = useQueryClient();

  // Fetch instruction files
  const {
    data: filesData,
    isLoading,
    error,
  } = useQuery<InstructionFilesResponse>({
    queryKey: ["instruction-files", page, filters, token, locale],
    queryFn: async () => {
      try {
        const queryParams: Record<string, string> = {
          page: page.toString(),
          page_size: "10",
        };
        
        if (filters.is_active) {
          queryParams.is_active = filters.is_active;
        }
        
        if (filters.file_type) {
          queryParams.file_type = filters.file_type;
        }

        return await fetchData({
          endpoint: "/api/admin-panel/instruction-files/",
          token,
          queryParams,
        });
      } catch (err: any) {
        console.error("Failed to fetch instruction files:", err);
        toast.error(
          extract_error(err) || err?.message || "Failed to load instruction files"
        );
        throw err;
      }
    },
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  // Fetch all instruction files to check for duplicates (for validation)
  const { data: allFilesData } = useQuery<InstructionFilesResponse | null>({
    queryKey: ["instruction-files-all", token, locale],
    queryFn: async (): Promise<InstructionFilesResponse | null> => {
      try {
        return await fetchData<InstructionFilesResponse>({
          endpoint: "/api/admin-panel/instruction-files/",
          token,
          queryParams: {
            page: "1",
            page_size: "1000", // Large page size to get all files for validation
          },
        });
      } catch (err: any) {
        console.error("Failed to fetch all instruction files:", err);
        return null;
      }
    },
    enabled: !!token,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    watch,
  } = useForm<StaticFilesFormData>({
    defaultValues: {
      file_type: "",
      title: "",
      description: "",
      is_active: "true",
    },
    mode: "onChange",
  });

  const selectedFileForForm = watch("file");

  // Get file types that are already used (for disabling in create form)
  const getUsedFileTypes = (): string[] => {
    const allFiles = allFilesData?.data?.instruction_files || [];
    return allFiles.map((file: InstructionFile) => file.file_type);
  };

  const usedFileTypes = getUsedFileTypes();

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: StaticFilesFormData) => {
      const formData = new FormData();
      formData.append("file_type", data.file_type);
      formData.append("title", data.title);
      formData.append("description", data.description);
      formData.append("is_active", data.is_active);
      
      if (data.file && data.file.length > 0) {
        formData.append("file", data.file[0]);
      }

      return postFormData({
        endpoint: "/api/admin-panel/instruction-files",
        token,
        body: formData,
        noToast: false, // Let API show toast
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["instruction-files"] });
      queryClient.invalidateQueries({ queryKey: ["instruction-files-all"] });
      setShowFormModal(false);
      reset();
      setSelectedFile(null);
      setIsEditing(false);
    },
    onError: () => {
      // Error toast is handled by postFormData
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: StaticFilesFormData }) => {
      const hasNewFile = data.file && data.file.length > 0;
      
      if (hasNewFile) {
        // If a new file is selected, use PUT with all fields including file
        // Note: file_type is not included as it cannot be changed
        const formData = new FormData();
        formData.append("title", data.title || "");
        formData.append("description", data.description || "");
        formData.append("is_active", data.is_active);
        formData.append("file", data.file[0]);

        return putData({
          endpoint: `/api/admin-panel/instruction-files/${id}/`,
          token,
          body: formData,
          isFormData: true,
        });
      } else {
        // If no new file, use PATCH to update only non-file fields
        // Note: file_type is not included as it cannot be changed
        const formData = new FormData();
        formData.append("title", data.title || "");
        formData.append("description", data.description || "");
        formData.append("is_active", data.is_active);
        // Don't include file field - API should keep existing file

        return patchData({
          endpoint: `/api/admin-panel/instruction-files/${id}/`,
          token,
          body: formData,
          isFormData: true,
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["instruction-files"] });
      queryClient.invalidateQueries({ queryKey: ["instruction-files-all"] });
      toast.success(trans.staticFiles?.updateSuccess || "File updated successfully");
      setShowFormModal(false);
      reset();
      setSelectedFile(null);
      setIsEditing(false);
    },
    onError: (error: any) => {
      const errorMessage =
        extract_error(error) || error?.message || "Failed to update file";
      toast.error(errorMessage);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      deleteData({
        endpoint: `/api/admin-panel/instruction-files/${id}`,
        token,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["instruction-files"] });
      queryClient.invalidateQueries({ queryKey: ["instruction-files-all"] });
      toast.success(trans.staticFiles?.deleteSuccess || "File deleted successfully");
      setShowDeleteModal(false);
      setSelectedFile(null);
    },
    onError: (error: any) => {
      const errorMessage =
        extract_error(error) || error?.message || "Failed to delete file";
      toast.error(errorMessage);
    },
  });

  const onSubmit: SubmitHandler<StaticFilesFormData> = (data) => {
    if (isEditing && selectedFile) {
      updateMutation.mutate({ id: selectedFile.id, data });
    } else {
      if (!data.file || data.file.length === 0) {
        toast.error(trans.staticFiles?.fileRequired || "File is required");
        return;
      }
      
      // Check if file type already exists
      if (usedFileTypes.includes(data.file_type)) {
        const fileTypeLabel = FILE_TYPES.find(ft => ft.value === data.file_type);
        const displayName = fileTypeLabel 
          ? (locale === "ar" ? fileTypeLabel.label_ar : fileTypeLabel.label_en)
          : data.file_type;
        toast.error(
          trans.staticFiles?.duplicateFileTypeError || 
          `A file with type "${displayName}" already exists. Please choose a different file type.`
        );
        return;
      }
      
      createMutation.mutate(data);
    }
  };

  const handleEdit = (file: InstructionFile) => {
    setSelectedFile(file);
    setIsEditing(true);
    reset({
      // Don't set file_type in edit mode since it can't be changed
      title: file.title || "",
      description: file.description || "",
      is_active: file.is_active ? "true" : "false",
    });
    setShowFormModal(true);
  };

  const handleDelete = (file: InstructionFile) => {
    setSelectedFile(file);
    setShowDeleteModal(true);
  };

  const handleAddNew = () => {
    setSelectedFile(null);
    setIsEditing(false);
    reset({
      file_type: "",
      title: "",
      description: "",
      is_active: "true",
    });
    setShowFormModal(true);
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  if (isLoading) {
    return <IsLoading />;
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500">
          {trans.staticFiles?.loadError || "Failed to load instruction files"}
        </p>
      </div>
    );
  }

  const files = filesData?.data?.instruction_files || [];
  const pagination = filesData?.data?.pagination;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-xl sm:text-2xl font-bold">
          {trans.staticFiles?.title || "Static Files"}
        </h1>
        <Button onClick={handleAddNew} className="w-full sm:w-auto flex items-center justify-center gap-2">
          <FaPlus />
          <span className="hidden sm:inline">{trans.staticFiles?.addNew || "Add New File"}</span>
          <span className="sm:hidden">{trans.staticFiles?.addNew || "Add New"}</span>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 p-3 sm:p-4 bg-muted rounded-lg">
        <div className="flex-1 w-full sm:min-w-[200px]">
          <label className="block text-sm font-medium mb-2">
            {trans.staticFiles?.filters?.isActive || "Active Status"}
          </label>
          <select
            value={filters.is_active}
            onChange={(e) => handleFilterChange("is_active", e.target.value)}
            className="w-full p-2 border rounded-md bg-background"
          >
            <option value="">{trans.staticFiles?.filters?.all || "All"}</option>
            <option value="true">{trans.staticFiles?.filters?.active || "Active"}</option>
            <option value="false">{trans.staticFiles?.filters?.inactive || "Inactive"}</option>
          </select>
        </div>
        <div className="flex-1 w-full sm:min-w-[200px]">
          <label className="block text-sm font-medium mb-2">
            {trans.staticFiles?.filters?.fileType || "File Type"}
          </label>
          <select
            value={filters.file_type}
            onChange={(e) => handleFilterChange("file_type", e.target.value)}
            className="w-full p-2 border rounded-md bg-background"
          >
            <option value="">{trans.staticFiles?.filters?.all || "All"}</option>
            {FILE_TYPES.map((fileType) => (
              <option key={fileType.value} value={fileType.value}>
                {locale === "ar" ? fileType.label_ar : fileType.label_en}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Desktop Table */}
      <div className="hidden xl:block">
        <div className="bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-xs md:text-sm">
              <thead>
                <tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.staticFiles?.tableHeaders?.fileType || "File Type"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.staticFiles?.tableHeaders?.title || "Title"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.staticFiles?.tableHeaders?.description || "Description"}
                  </th>
                  <th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.staticFiles?.tableHeaders?.version || "Version"}
                  </th>
                  <th className="text-center py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.staticFiles?.tableHeaders?.status || "Status"}
                  </th>
                  <th className="text-center py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
                    {trans.staticFiles?.tableHeaders?.actions || "Actions"}
                  </th>
                </tr>
              </thead>
              <tbody>
                {files.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                      {trans.staticFiles?.noFiles || "No files found"}
                    </td>
                  </tr>
                ) : (
                  files.map((file) => (
                    <tr
                      key={file.id}
                      className="border-b border-border hover:bg-muted transition-colors"
                    >
                      <td className="py-3 px-4 font-bold text-foreground">
                        {file.file_type_display || file.file_type}
                      </td>
                      <td className="py-3 px-4 text-foreground">
                        {file.title || "-"}
                      </td>
                      <td className="py-3 px-4 text-foreground">
                        <span className="text-muted-foreground line-clamp-2">
                          {file.description || "-"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-foreground">
                        {file.version}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center">
                          {file.is_active ? (
                            <span className="inline-flex items-center gap-1 text-green-600">
                              <FaCheckCircle />
                              <span className="text-sm">{trans.staticFiles?.active || "Active"}</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-red-600">
                              <FaTimesCircle />
                              <span className="text-sm">{trans.staticFiles?.inactive || "Inactive"}</span>
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-center gap-2">
                          {file.file_url && (
                            <a
                              href={file.file_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 hover:bg-muted text-primary hover:text-primary/80 rounded transition-colors"
                              title={trans.staticFiles?.download || "Download"}
                            >
                              <FaDownload className="text-base" />
                            </a>
                          )}
                          <Button
                            onClick={() => handleEdit(file)}
                            variant="ghost"
                            className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors"
                            title={trans.staticFiles?.edit || "Edit"}
                          >
                            <FaEdit className="text-base" />
                          </Button>
                          <Button
                            onClick={() => handleDelete(file)}
                            variant="ghost"
                            className="p-1.5 hover:bg-muted text-red-600 hover:text-red-700 transition-colors"
                            title={trans.staticFiles?.delete || "Delete"}
                          >
                            <FaTrash className="text-base" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {pagination && pagination.num_pages > 1 && (
            <div className="flex items-center justify-between px-4 md:px-6 py-4 border-t-2 border-border">
              <div className="text-xs md:text-sm text-muted-foreground">
                {trans.pagination?.table || "Page"} {pagination.current_page} {trans.pagination?.of || "of"}{" "}
                {pagination.num_pages} {trans.pagination?.tables || "pages"}
              </div>
              <Pagination
                currentPage={pagination.current_page}
                onPageChange={setPage}
                locale={locale}
                totalPages={pagination.num_pages}
              />
            </div>
          )}
        </div>
      </div>

      {/* Mobile Cards */}
      <div className="xl:hidden space-y-4">
        {files.length === 0 ? (
          <div className="bg-card rounded-xl shadow-lg border-2 border-border p-8 text-center">
            <p className="text-muted-foreground">
              {trans.staticFiles?.noFiles || "No files found"}
            </p>
          </div>
        ) : (
          files.map((file) => (
            <div
              key={file.id}
              className="bg-card rounded-xl shadow-lg border-2 border-border p-4 hover:shadow-xl hover:border-primary/60 transition-all"
            >
              <div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
                <div className="flex-1">
                  <h3 className="font-bold text-base md:text-lg text-foreground mb-1">
                    {file.file_type_display || file.file_type}
                  </h3>
                  {file.title && (
                    <p className="text-xs text-muted-foreground">
                      {file.title}
                    </p>
                  )}
                </div>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                    file.is_active
                      ? "bg-green-50 text-green-700 border-green-200"
                      : "bg-red-50 text-red-700 border-red-200"
                  }`}
                >
                  {file.is_active ? (
                    <>
                      <FaCheckCircle className="mr-1" />
                      {trans.staticFiles?.active || "Active"}
                    </>
                  ) : (
                    <>
                      <FaTimesCircle className="mr-1" />
                      {trans.staticFiles?.inactive || "Inactive"}
                    </>
                  )}
                </span>
              </div>
              {file.description && (
                <div className="mb-3 pb-3 border-b border-border">
                  <p className="text-xs text-muted-foreground mb-1">
                    {trans.staticFiles?.tableHeaders?.description || "Description"}
                  </p>
                  <p className="text-sm text-foreground line-clamp-3">
                    {file.description}
                  </p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div className="bg-muted/50 p-2 rounded-lg">
                  <p className="text-xs text-muted-foreground mb-1">
                    {trans.staticFiles?.tableHeaders?.version || "Version"}
                  </p>
                  <p className="font-semibold text-sm text-foreground">
                    {file.version}
                  </p>
                </div>
                {file.file_url && (
                  <div className="bg-muted/50 p-2 rounded-lg">
                    <p className="text-xs text-muted-foreground mb-1">
                      {trans.staticFiles?.download || "File"}
                    </p>
                    <a
                      href={file.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-semibold text-sm text-primary hover:underline"
                    >
                      {trans.staticFiles?.download || "Download"}
                    </a>
                  </div>
                )}
              </div>
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                {file.file_url && (
                  <a
                    href={file.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 hover:bg-muted text-primary hover:text-primary/80 rounded transition-colors"
                    title={trans.staticFiles?.download || "Download"}
                  >
                    <FaDownload className="text-base" />
                  </a>
                )}
                <Button
                  onClick={() => handleEdit(file)}
                  variant="ghost"
                  className="p-2 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors"
                  title={trans.staticFiles?.edit || "Edit"}
                >
                  <FaEdit className="text-base" />
                </Button>
                <Button
                  onClick={() => handleDelete(file)}
                  variant="ghost"
                  className="p-2 hover:bg-muted text-red-600 hover:text-red-700 transition-colors"
                  title={trans.staticFiles?.delete || "Delete"}
                >
                  <FaTrash className="text-base" />
                </Button>
              </div>
            </div>
          ))
        )}
        {pagination && pagination.num_pages > 1 && (
          <div className="flex flex-col items-center gap-3 pt-4">
            <div className="text-xs text-muted-foreground">
              {trans.pagination?.table || "Page"} {pagination.current_page} {trans.pagination?.of || "of"}{" "}
              {pagination.num_pages} {trans.pagination?.tables || "pages"}
            </div>
            <Pagination
              currentPage={pagination.current_page}
              onPageChange={setPage}
              locale={locale}
              totalPages={pagination.num_pages}
            />
          </div>
        )}
      </div>


      {/* Create/Edit Modal */}
      <GlobalModal
        isOpen={showFormModal}
        onClose={() => {
          setShowFormModal(false);
          reset();
          setSelectedFile(null);
          setIsEditing(false);
        }}
      >
        <div className="p-4 sm:p-6">
          <h2 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6">
            {isEditing
              ? trans.staticFiles?.editTitle || "Edit File"
              : trans.staticFiles?.createTitle || "Add New File"}
          </h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 sm:space-y-6">
          {/* File Type - Only show when creating, not when editing */}
          {!isEditing && (
            <div>
              <label className="block text-sm font-medium mb-2">
                {trans.staticFiles?.form?.fileType || "File Type"} *
              </label>
              <select
                {...register("file_type", {
                  required: !isEditing ? (trans.staticFiles?.form?.fileTypeRequired || "File type is required") : false,
                })}
                className="w-full p-2 sm:p-3 border rounded-md bg-background text-sm sm:text-base"
              >
                <option value="">
                  {trans.staticFiles?.form?.selectFileType || "Select file type..."}
                </option>
                {FILE_TYPES.map((fileType) => {
                  const isDisabled = usedFileTypes.includes(fileType.value);
                  return (
                    <option 
                      key={fileType.value} 
                      value={fileType.value}
                      disabled={isDisabled}
                      style={isDisabled ? { color: '#999', fontStyle: 'italic' } : {}}
                    >
                      {locale === "ar" ? fileType.label_ar : fileType.label_en}
                      {isDisabled && ` ${trans.staticFiles?.alreadyUsed || "(Already used)"}`}
                    </option>
                  );
                })}
              </select>
              {errors.file_type && (
                <p className="text-red-500 text-sm mt-1">{errors.file_type.message}</p>
              )}
              {usedFileTypes.length > 0 && (
                <p className="text-xs text-muted-foreground mt-1">
                  {trans.staticFiles?.disabledFileTypesNote || "Some file types are disabled because they already exist."}
                </p>
              )}
            </div>
          )}
          
          {/* Show file type as read-only when editing */}
          {isEditing && selectedFile && (
            <div>
              <label className="block text-sm font-medium mb-2">
                {trans.staticFiles?.form?.fileType || "File Type"}
              </label>
              <div className="w-full p-2 sm:p-3 border rounded-md bg-muted text-sm sm:text-base">
                {selectedFile.file_type_display || selectedFile.file_type}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {trans.staticFiles?.fileTypeNotEditable || "File type cannot be changed after creation."}
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-2">
              {trans.staticFiles?.form?.title || "Title"}
            </label>
            <input
              type="text"
              {...register("title")}
              className="w-full p-2 sm:p-3 border rounded-md bg-background text-sm sm:text-base"
              placeholder={trans.staticFiles?.form?.titlePlaceholder || "Enter title"}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              {trans.staticFiles?.form?.file || "File"} {!isEditing && "*"}
            </label>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              {...register("file", {
                required: !isEditing ? (trans.staticFiles?.form?.fileRequired || "File is required") : false,
              })}
              className="w-full p-2 sm:p-3 border rounded-md bg-background text-sm sm:text-base file:mr-2 sm:file:mr-4 file:py-1.5 sm:file:py-2 file:px-2 sm:file:px-4 file:rounded-lg file:border-0 file:text-xs sm:file:text-sm file:font-semibold file:bg-primary file:text-black hover:file:bg-primary/90"
            />
            {errors.file && (
              <p className="text-red-500 text-sm mt-1">{errors.file.message}</p>
            )}
            {isEditing && selectedFile && (
              <p className="text-sm text-muted-foreground mt-1">
                {trans.staticFiles?.form?.fileNote || "Leave empty to keep current file"}
              </p>
            )}
            {selectedFileForForm && selectedFileForForm.length > 0 && (
              <p className="text-sm text-muted-foreground mt-1">
                {trans.staticFiles?.form?.selectedFile || "Selected:"} {selectedFileForForm[0].name}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              {trans.staticFiles?.form?.description || "Description"}
            </label>
            <textarea
              {...register("description")}
              rows={4}
              className="w-full p-2 sm:p-3 border rounded-md bg-background text-sm sm:text-base resize-y"
              placeholder={trans.staticFiles?.form?.descriptionPlaceholder || "Enter description"}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              {trans.staticFiles?.form?.isActive || "Active Status"}
            </label>
            <select
              {...register("is_active")}
              className="w-full p-2 sm:p-3 border rounded-md bg-background text-sm sm:text-base"
            >
              <option value="true">{trans.staticFiles?.active || "Active"}</option>
              <option value="false">{trans.staticFiles?.inactive || "Inactive"}</option>
            </select>
          </div>

            <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 pt-4 sm:pt-6">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowFormModal(false);
                  reset();
                  setSelectedFile(null);
                  setIsEditing(false);
                }}
                className="w-full sm:w-auto"
              >
                {trans.staticFiles?.cancel || "Cancel"}
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="w-full sm:w-auto"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? trans.staticFiles?.saving || "Saving..."
                  : isEditing
                  ? trans.staticFiles?.update || "Update"
                  : trans.staticFiles?.create || "Create"}
              </Button>
            </div>
          </form>
        </div>
      </GlobalModal>

      {/* Delete Confirmation Modal */}
      <GlobalModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false);
          setSelectedFile(null);
        }}
      >
        <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
          <h2 className="text-xl sm:text-2xl font-bold">
            {trans.staticFiles?.deleteTitle || "Delete File"}
          </h2>
          <p className="text-sm sm:text-base">
            {trans.staticFiles?.deleteMessage || "Are you sure you want to delete this file? This action cannot be undone."}
          </p>
          {selectedFile && (
            <div className="p-3 sm:p-4 bg-muted rounded-md">
              <p className="font-semibold text-sm sm:text-base">{selectedFile.file_type_display || selectedFile.file_type}</p>
              {selectedFile.title && <p className="text-xs sm:text-sm text-muted-foreground mt-1">{selectedFile.title}</p>}
            </div>
          )}
          <div className="flex flex-col sm:flex-row justify-end gap-2 sm:gap-3 pt-2">
            <Button
              variant="outline"
              onClick={() => {
                setShowDeleteModal(false);
                setSelectedFile(null);
              }}
              className="w-full sm:w-auto"
            >
              {trans.staticFiles?.cancel || "Cancel"}
            </Button>
            <Button
              variant="destructive"
              onClick={() => selectedFile && deleteMutation.mutate(selectedFile.id)}
              disabled={deleteMutation.isPending}
              className="w-full sm:w-auto"
            >
              {deleteMutation.isPending
                ? trans.staticFiles?.deleting || "Deleting..."
                : trans.staticFiles?.deleteConfirm || "Yes, Delete"}
            </Button>
          </div>
        </div>
      </GlobalModal>
    </div>
  );
}
