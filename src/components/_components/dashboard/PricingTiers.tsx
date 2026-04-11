"use client";

import React, { useState, useMemo } from "react";
import { useForm, SubmitHandler } from "react-hook-form";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Locale } from "../../../../i18n.config";
import { fetchData } from "@/lib/api/fetchData";
import { postData } from "@/lib/api/postData";
import { putData } from "@/lib/api/putApi";
import { deleteData } from "@/lib/api/deleteApi";
import { toast } from "react-toastify";
import { Button } from "@/components/ui/button";
import IsLoading from "../ISloading";
import GlobalModal from "../GlobalModal";
import { extract_error } from "@/lib/api/errorApi";
import {
	FaEdit,
	FaTrash,
	FaPlus,
	FaCheckCircle,
	FaTimesCircle,
} from "react-icons/fa";
import Pagination from "../Pagination";
import { VEHICLE_TYPES } from "@/lib/constants/vehicleTypes";
import CustomSelectInput from "../ControlledFields/CustomSelectInput";

type PricingTier = {
	id: number;
	vehicle_type: {
		id: number;
		name_en: string;
		name_ar: string;
	};
	min_distance_miles: string;
	max_distance_miles: string;
	rate_per_mile: string;
	order: number;
	is_active: boolean;
};

type VehicleType = {
	id: number;
	name_en: string;
	name_ar: string;
};

type PricingTiersResponse = {
	success: boolean;
	message: string;
	data: PricingTier[];
	pagination: {
		count: number;
		num_pages: number;
		current_page: number;
		page_size: number;
	};
};

type VehicleTypesResponse = {
	success: boolean;
	data: VehicleType[];
};

type TierFormData = {
	vehicle_type_ids: number[] |string[];
	min_distance_miles: string;
	max_distance_miles: string;
	rate_per_mile: string;
	order: number;
	is_active: boolean;
};

type PricingTiersProps = {
	trans: any;
	token?: string;
	locale: Locale;
};

export default function PricingTiers({
	trans,
	token,
	locale,
}: PricingTiersProps) {
	const [page, setPage] = useState(1);
	const [showFormModal, setShowFormModal] = useState(false);
	const [showDeleteModal, setShowDeleteModal] = useState(false);
	const [selectedTier, setSelectedTier] = useState<PricingTier | null>(null);
	const [isEditing, setIsEditing] = useState(false);
	const queryClient = useQueryClient();

	// Fetch tiers
	const {
		data: tiersData,
		isLoading,
		error,
	} = useQuery<PricingTiersResponse>({
		queryKey: ["pricing-tiers", page, token, locale],
		queryFn: async () => {
			try {
				return await fetchData({
					endpoint: "/api/pricing/tiers/",
					token,
					queryParams: {
						locale,
						page: page.toString(),
						page_size: "10",
					},
				});
			} catch (err: any) {
				console.error("Failed to fetch pricing tiers:", err);
				toast.error(
					extract_error(err) || err?.message || "Failed to load pricing tiers",
				);
				throw err;
			}
		},
		enabled: !!token,
		retry: 1,
		refetchOnWindowFocus: false,
	});

	// Use static vehicle types (no API endpoint for vehicle types)
	// const vehicleTypes = VEHICLE_TYPES.map((item) => ({
	// 	label: item[`name_${locale}`],
	// 	value: item.id.toString(),
	// }));

const { data: vehicleTypes =[] ,isLoading :isLoadingVehicleTypes } =
  useQuery({
    queryKey: ["vehicle-types"],
    queryFn: async () =>
      fetchData<{ name_ar: string; name_en: string; id: number }[]>({ endpoint: "/api/vehicle/vehicle-types/" }),
    select: (data) =>
      data.map((item) => ({
        label: item.name_en,
        value: item.id.toString(),
      })),
  }) || [];
	const {
		register,
		handleSubmit,
		reset,
		control,
		formState: { errors },
	} = useForm<TierFormData>({
		defaultValues: {
			vehicle_type_ids: [],
			min_distance_miles: "0.00",
			max_distance_miles: "0.00",
			rate_per_mile: "0.00",
			order: 0,
			is_active: true,
		},
	});

	// Create mutation
	const createMutation = useMutation({
		mutationFn: (data: TierFormData) =>
			postData({
				endpoint: "/api/pricing/tiers/",
				token,
				body: data,
				queryParams: { locale },
				noToast: false, // Let API show toast
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["pricing-tiers"] });
			setShowFormModal(false);
			reset();
			setSelectedTier(null);
			setIsEditing(false);
		},
		onError: () => {
			// Error toast is handled by postData
		},
	});

	// Update mutation
	const updateMutation = useMutation({
		mutationFn: ({ id, data }: { id: number; data: TierFormData }) =>
			putData({
				endpoint: `/api/pricing/tiers/${id}/`,
				token,
				body: data,
				queryParams: { locale },
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["pricing-tiers"] });
			toast.success(trans.tiers?.updateSuccess || "Tier updated successfully");
			setShowFormModal(false);
			reset();
			setSelectedTier(null);
			setIsEditing(false);
		},
		onError: (error: any) => {
			const errorMessage =
				extract_error(error) || error?.message || "Failed to update tier";
			toast.error(errorMessage);
		},
	});

	// Delete mutation
	const deleteMutation = useMutation({
		mutationFn: (id: number) =>
			deleteData({
				endpoint: `/api/pricing/tiers/${id}`,
				token,
				queryParams: { locale },
			}),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["pricing-tiers"] });
			toast.success(trans.tiers?.deleteSuccess || "Tier deleted successfully");
			setShowDeleteModal(false);
			setSelectedTier(null);
		},
		onError: (error: any) => {
			const errorMessage =
				extract_error(error) || error?.message || "Failed to delete tier";
			toast.error(errorMessage);
		},
	});

	const handleCreate = () => {
		setIsEditing(false);
		setSelectedTier(null);
		reset({
			vehicle_type_ids: [],
			min_distance_miles: "0.00",
			max_distance_miles: "0.00",
			rate_per_mile: "0.00",
			order: 0,
			is_active: true,
		});
		setShowFormModal(true);
	};

	const handleEdit = (tier: PricingTier) => {
		setIsEditing(true);
		setSelectedTier(tier);
		reset({
			vehicle_type_ids: [tier.vehicle_type.id.toString()],
			min_distance_miles: tier.min_distance_miles,
			max_distance_miles: tier.max_distance_miles,
			rate_per_mile: tier.rate_per_mile,
			order: tier.order,
			is_active: tier.is_active,
		});
		setShowFormModal(true);
	};

	const handleDelete = (tier: PricingTier) => {
		setSelectedTier(tier);
		setShowDeleteModal(true);
	};

	const onSubmit: SubmitHandler<TierFormData> = (data) => {
		if (isEditing && selectedTier) {
			updateMutation.mutate({ id: selectedTier.id, data });
		} else {
			createMutation.mutate(data);
		}
	};

	const handleDeleteConfirm = () => {
		if (selectedTier) {
			deleteMutation.mutate(selectedTier.id);
		}
	};

	// Sort tiers by order field
	const tiers = useMemo(() => {
		const data = tiersData?.data || [];
		return [...data].sort((a, b) => a.order - b.order);
	}, [tiersData?.data]);

	const pagination = tiersData?.pagination || {
		count: 0,
		num_pages: 1,
		current_page: 1,
		page_size: 10,
	};

	if (isLoading) {
		return (
			<div className="flex justify-center items-center min-h-[400px]">
				<IsLoading />
			</div>
		);
	}

	if (error) {
		return (
			<div className="bg-card rounded-xl shadow-xl border-2 border-border p-6">
				<div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
					<p className="text-red-700 font-medium">
						{trans.tiers?.loadError ||
							"Failed to load pricing tiers. Please try again."}
					</p>
				</div>
			</div>
		);
	}

	return (
		<div>
			{/* Header with Add Button */}
			<div className="flex items-center justify-between mb-4">
				<Button
					onClick={handleCreate}
					className="w-full sm:w-auto bg-primary hover:bg-primary/90 text-foreground font-semibold shadow-lg shadow-primary/30 text-sm md:text-base"
				>
					<FaPlus className="mr-2" />
					{trans.tiers?.addButton || "Add Tier"}
				</Button>
			</div>

			{tiers.length === 0 ? (
				<div className="bg-card rounded-xl shadow-xl border-2 border-border p-8 md:p-12 text-center">
					<p className="text-muted-foreground text-base md:text-lg">
						{trans.tiers?.empty || "No pricing tiers found"}
					</p>
				</div>
			) : (
				<>
					{/* Desktop Table */}
					<div className="hidden xl:block">
						<div className="bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden">
							<div className="overflow-x-auto">
								<table className="w-full min-w-[800px] text-xs md:text-sm">
									<thead>
										<tr className="border-b-2 border-border bg-gray-100 dark:bg-gray-800">
											<th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
												{trans.tiers?.vehicleType || "Vehicle Type"}
											</th>
											<th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
												{trans.tiers?.minDistance || "Min Distance"}
											</th>
											<th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
												{trans.tiers?.maxDistance || "Max Distance"}
											</th>
											<th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
												{trans.tiers?.ratePerMile || "Rate/Mile"}
											</th>
											<th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
												{trans.tiers?.order || "Order"}
											</th>
											<th className="text-start py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
												{trans.tiers?.status || "Status"}
											</th>
											<th className="text-center py-4 px-4 text-sm font-bold text-gray-900 dark:text-gray-100 uppercase tracking-wide">
												{trans.tiers?.actions || "Actions"}
											</th>
										</tr>
									</thead>
									<tbody>
										{tiers.map((tier) => (
											<tr
												key={tier.id}
												className="border-b border-border hover:bg-muted transition-colors"
											>
												<td className="py-3 px-4 font-bold text-foreground">
													{locale === "ar"
														? tier.vehicle_type.name_ar
														: tier.vehicle_type.name_en}
												</td>
												<td className="py-3 px-4 text-foreground">
													{tier.min_distance_miles}{" "}
													{trans.tiers?.miles || "miles"}
												</td>
												<td className="py-3 px-4 text-foreground">
													{tier.max_distance_miles}{" "}
													{trans.tiers?.miles || "miles"}
												</td>
												<td className="py-3 px-4 text-foreground font-semibold">
													€{tier.rate_per_mile}
												</td>
												<td className="py-3 px-4 text-foreground">
													{tier.order}
												</td>
												<td className="py-3 px-4">
													<span
														className={`inline-flex items-center px-2.5 py-0.5 rounded-full font-bold ${
															tier.is_active
																? "bg-green-50 text-green-700 border border-green-200"
																: "bg-red-50 text-red-700 border border-red-200"
														}`}
													>
														{tier.is_active ? (
															<>
																<FaCheckCircle className="mr-1" />
																{trans.tiers?.active || "Active"}
															</>
														) : (
															<>
																<FaTimesCircle className="mr-1" />
																{trans.tiers?.inactive || "Inactive"}
															</>
														)}
													</span>
												</td>
												<td className="py-3 px-4">
													<div className="flex items-center justify-center gap-2">
														<Button
															onClick={() => handleEdit(tier)}
															variant="ghost"
															className="p-1.5 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors"
															title={trans.tiers?.edit || "Edit"}
														>
															<FaEdit className="text-base" />
														</Button>
														<Button
															onClick={() => handleDelete(tier)}
															variant="ghost"
															className="p-1.5 hover:bg-muted text-red-600 hover:text-red-700 transition-colors"
															title={trans.tiers?.delete || "Delete"}
														>
															<FaTrash className="text-base" />
														</Button>
													</div>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
							{pagination.num_pages > 1 && (
								<div className="flex items-center justify-between px-4 md:px-6 py-4 border-t-2 border-border">
									<div className="text-xs md:text-sm text-muted-foreground">
										{trans.pagination?.table || "Page"} {page}{" "}
										{trans.pagination?.of || "of"} {pagination.num_pages}{" "}
										{trans.pagination?.tables || "pages"}
									</div>
									<Pagination
										currentPage={page}
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
						{tiers.map((tier) => (
							<div
								key={tier.id}
								className="bg-card rounded-xl shadow-lg border-2 border-border p-4 hover:shadow-xl hover:border-primary/60 transition-all"
							>
								<div className="flex items-start justify-between mb-3 pb-3 border-b-2 border-border">
									<div className="flex-1">
										<h3 className="font-bold text-base md:text-lg text-foreground mb-1">
											{locale === "ar"
												? tier.vehicle_type.name_ar
												: tier.vehicle_type.name_en}
										</h3>
										<p className="text-xs text-muted-foreground">
											{trans.tiers?.order || "Order"}: {tier.order}
										</p>
									</div>
									<span
										className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${
											tier.is_active
												? "bg-green-50 text-green-700 border-green-200"
												: "bg-red-50 text-red-700 border-red-200"
										}`}
									>
										{tier.is_active ? (
											<>
												<FaCheckCircle className="mr-1" />
												{trans.tiers?.active || "Active"}
											</>
										) : (
											<>
												<FaTimesCircle className="mr-1" />
												{trans.tiers?.inactive || "Inactive"}
											</>
										)}
									</span>
								</div>
								<div className="grid grid-cols-2 gap-3 mb-3">
									<div className="bg-muted/50 p-2 rounded-lg">
										<p className="text-xs text-muted-foreground mb-1">
											{trans.tiers?.minDistance || "Min Distance"}
										</p>
										<p className="font-semibold text-sm text-foreground">
											{tier.min_distance_miles} {trans.tiers?.miles || "miles"}
										</p>
									</div>
									<div className="bg-muted/50 p-2 rounded-lg">
										<p className="text-xs text-muted-foreground mb-1">
											{trans.tiers?.maxDistance || "Max Distance"}
										</p>
										<p className="font-semibold text-sm text-foreground">
											{tier.max_distance_miles} {trans.tiers?.miles || "miles"}
										</p>
									</div>
									<div className="bg-muted/50 p-2 rounded-lg">
										<p className="text-xs text-muted-foreground mb-1">
											{trans.tiers?.ratePerMile || "Rate/Mile"}
										</p>
										<p className="font-semibold text-sm text-foreground">
											€{tier.rate_per_mile}
										</p>
									</div>
								</div>
								<div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
									<Button
										onClick={() => handleEdit(tier)}
										variant="ghost"
										className="p-2 hover:bg-muted text-yellow-600 hover:text-yellow-700 transition-colors"
										title={trans.tiers?.edit || "Edit"}
									>
										<FaEdit className="text-base" />
									</Button>
									<Button
										onClick={() => handleDelete(tier)}
										variant="ghost"
										className="p-2 hover:bg-muted text-red-600 hover:text-red-700 transition-colors"
										title={trans.tiers?.delete || "Delete"}
									>
										<FaTrash className="text-base" />
									</Button>
								</div>
							</div>
						))}
						{pagination.num_pages > 1 && (
							<div className="flex flex-col items-center gap-3 pt-4">
								<div className="text-xs text-muted-foreground">
									{trans.pagination?.table || "Page"} {page}{" "}
									{trans.pagination?.of || "of"} {pagination.num_pages}{" "}
									{trans.pagination?.tables || "pages"}
								</div>
								<Pagination
									currentPage={page}
									onPageChange={setPage}
									locale={locale}
									totalPages={pagination.num_pages}
								/>
							</div>
						)}
					</div>
				</>
			)}

			{/* Create/Edit Modal */}
			<GlobalModal
				isOpen={showFormModal}
				onClose={() => {
					if (!createMutation.isPending && !updateMutation.isPending) {
						setShowFormModal(false);
						reset();
						setSelectedTier(null);
						setIsEditing(false);
					}
				}}
			>
				<div className="p-4 md:p-6 w-full">
					<h2 className="text-lg md:text-xl font-bold text-foreground mb-4 md:mb-6">
						{isEditing
							? trans.tiers?.editTitle || "Edit Pricing Tier"
							: trans.tiers?.createTitle || "Create New Pricing Tier"}
					</h2>

					<form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
						<div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
							{/* Vehicle Type */}
							<div>
								<CustomSelectInput
									name="vehicle_type_ids"
									label={trans.tiers?.vehicleType || "Vehicle Type"}
									control={control}
									options={vehicleTypes || []}
                  isLoading={isLoadingVehicleTypes}
									required
									containerClassName="col-span-1 md:col-span-2"
									isMulti
								/>

								{errors.vehicle_type_ids && (
									<p className="text-error text-sm mt-1">
										{errors.vehicle_type_ids.message}
									</p>
								)}
							</div>

							{/* Order */}
							<div>
								<label className="block text-sm font-medium text-foreground mb-2">
									{trans.tiers?.order || "Order"}
									<span className="text-red-500 ml-1">*</span>
								</label>
								<input
									type="number"
									{...register("order", {
										required: trans.tiers?.orderRequired || "Order is required",
										valueAsNumber: true,
										min: {
											value: 0,
											message:
												trans.tiers?.orderMin || "Order must be 0 or greater",
										},
									})}
									className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
								/>
								{errors.order && (
									<p className="text-error text-sm mt-1">
										{errors.order.message}
									</p>
								)}
							</div>

							{/* Min Distance */}
							<div>
								<label className="block text-sm font-medium text-foreground mb-2">
									{trans.tiers?.minDistance || "Min Distance (Miles)"}
									<span className="text-red-500 ml-1">*</span>
								</label>
								<input
									type="text"
									{...register("min_distance_miles", {
										required:
											trans.tiers?.minDistanceRequired ||
											"Min distance is required",
										pattern: {
											value: /^\d+(\.\d{1,2})?$/,
											message:
												trans.tiers?.minDistanceInvalid ||
												"Invalid distance format",
										},
									})}
									placeholder="0.00"
									className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
								/>
								{errors.min_distance_miles && (
									<p className="text-error text-sm mt-1">
										{errors.min_distance_miles.message}
									</p>
								)}
							</div>

							{/* Max Distance */}
							<div>
								<label className="block text-sm font-medium text-foreground mb-2">
									{trans.tiers?.maxDistance || "Max Distance (Miles)"}
									<span className="text-red-500 ml-1">*</span>
								</label>
								<input
									type="text"
									{...register("max_distance_miles", {
										required:
											trans.tiers?.maxDistanceRequired ||
											"Max distance is required",
										pattern: {
											value: /^\d+(\.\d{1,2})?$/,
											message:
												trans.tiers?.maxDistanceInvalid ||
												"Invalid distance format",
										},
									})}
									placeholder="10.00"
									className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
								/>
								{errors.max_distance_miles && (
									<p className="text-error text-sm mt-1">
										{errors.max_distance_miles.message}
									</p>
								)}
							</div>

							{/* Rate Per Mile */}
							<div>
								<label className="block text-sm font-medium text-foreground mb-2">
									{trans.tiers?.ratePerMile || "Rate Per Mile"}
									<span className="text-red-500 ml-1">*</span>
								</label>
								<input
									type="text"
									{...register("rate_per_mile", {
										required:
											trans.tiers?.ratePerMileRequired ||
											"Rate per mile is required",
										pattern: {
											value: /^\d+(\.\d{1,2})?$/,
											message:
												trans.tiers?.ratePerMileInvalid ||
												"Invalid rate format",
										},
									})}
									placeholder="2.50"
									className="w-full p-3 border-2 border-border rounded-lg bg-background text-foreground focus:outline-none focus:border-primary transition-colors"
								/>
								{errors.rate_per_mile && (
									<p className="text-error text-sm mt-1">
										{errors.rate_per_mile.message}
									</p>
								)}
							</div>

							{/* Is Active */}
							<div className="flex items-center">
								<label className="flex items-center cursor-pointer group">
									<input
										type="checkbox"
										{...register("is_active")}
										className="w-5 h-5 text-primary bg-background border-2 border-border rounded focus:ring-2 focus:ring-primary focus:ring-offset-2 cursor-pointer transition-colors"
									/>
									<span className="ml-3 text-sm font-medium text-foreground group-hover:text-primary transition-colors">
										{trans.tiers?.isActive || "Is Active"}
									</span>
								</label>
							</div>
						</div>

						<div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-4 border-t-2 border-border">
							<Button
								type="button"
								variant="secondary"
								onClick={() => {
									setShowFormModal(false);
									reset();
									setSelectedTier(null);
									setIsEditing(false);
								}}
								disabled={createMutation.isPending || updateMutation.isPending}
								className="w-full sm:flex-1 font-semibold"
							>
								{trans.tiers?.cancel || "Cancel"}
							</Button>
							<Button
								type="submit"
								disabled={createMutation.isPending || updateMutation.isPending}
								className="w-full sm:flex-1 font-semibold bg-primary hover:bg-primary/90 text-foreground shadow-lg shadow-primary/30"
							>
								{createMutation.isPending || updateMutation.isPending
									? trans.tiers?.saving || "Saving..."
									: isEditing
										? trans.tiers?.updateButton || "Update"
										: trans.tiers?.createButton || "Create"}
							</Button>
						</div>
					</form>
				</div>
			</GlobalModal>

			{/* Delete Confirmation Modal */}
			<GlobalModal
				isOpen={showDeleteModal}
				onClose={() => {
					if (!deleteMutation.isPending) {
						setShowDeleteModal(false);
						setSelectedTier(null);
					}
				}}
			>
				<div className="p-4 md:p-6 w-full">
					<h2 className="text-lg md:text-xl font-bold text-foreground mb-4">
						{trans.tiers?.deleteTitle || "Delete Pricing Tier"}
					</h2>
					<p className="text-sm text-muted-foreground mb-4">
						{trans.tiers?.deleteMessage ||
							"Are you sure you want to delete this pricing tier? This action cannot be undone."}
					</p>
					<div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mt-4">
						<Button
							type="button"
							variant="secondary"
							onClick={() => {
								setShowDeleteModal(false);
								setSelectedTier(null);
							}}
							disabled={deleteMutation.isPending}
							className="w-full sm:flex-1 font-semibold"
						>
							{trans.tiers?.cancel || "Cancel"}
						</Button>
						<Button
							type="button"
							onClick={handleDeleteConfirm}
							disabled={deleteMutation.isPending}
							className="w-full sm:flex-1 font-semibold bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30 disabled:opacity-60"
						>
							{deleteMutation.isPending
								? trans.tiers?.deleting || "Deleting..."
								: trans.tiers?.deleteConfirm || "Delete"}
						</Button>
					</div>
				</div>
			</GlobalModal>
		</div>
	);
}
