import React from "react";
import { Controller } from "react-hook-form";
import Select from "react-select";
import { StylesConfig } from "react-select";
import { selectStyles } from "./styles/select-styles";
import { cn } from "@/lib/utils";
interface CustomInputProps {
	label?: string;
	name: string;
	options: { value: string; label: string }[];
	placeholder?: string;
	error?: string;
	className?: string;
	control: any;
	required?: boolean;
	onHandleChange?: (selectedOption: any) => void;
	isLoading?: boolean;
	disabled?: boolean;
	defaultValue?: boolean;
	menuPosition?: "absolute" | "fixed";
	isClearable?: boolean;
	containerClassName?: string;
	subLabel?: string;
	labelClassName?: string;
	isMulti?: boolean;
}

function ControlledSelectComponent({
	label,
	name,
	options,
	placeholder = "",
	error,
	control,
	required = false,
	className = "",
	onHandleChange,
	isLoading = false,
	disabled = false,
	defaultValue,
	menuPosition = "absolute",
	isClearable = true,
	containerClassName = "",
	subLabel,
	labelClassName = "block text-sm font-medium text-foreground mb-2",
	isMulti = false,
}: CustomInputProps) {

	return (
		<div className={cn(containerClassName)}>
			{label && (
				<>
					<div className="flex ">
						<label htmlFor={name} className={cn(subLabel && "mb-2", labelClassName)}>
							{label}
							{required && <span className="ms-1 text-red-700">*</span>}
						</label>
					</div>
					{subLabel && <p className="text-sm text-black/80 mb-3">{subLabel}</p>}
				</>
			)}
			<Controller
				name={name}
				control={control}
				render={({ field }) => (
					<div className="relative">
						<Select
							{...field}
							options={options}
							placeholder={placeholder}
							styles={selectStyles}
							className={`nc-Select ${className}`}
							classNamePrefix="react-select"
							// isClearable={true}
							// isSearchable={true}
							menuPosition={menuPosition}
							// @ts-ignore
							onChange={(selectedOption) => {
								if (isMulti) {
									const values = selectedOption ? selectedOption.map((opt: any) => opt.value) : [];
									field.onChange(values);
									onHandleChange?.(values);
								} else {
									const value = selectedOption ? selectedOption.value : null;
									field.onChange(value);
									onHandleChange?.(value);
								}
							}}
				
							value={
								isMulti
									? options.filter((opt) => field.value?.includes(opt.value))
									: options.find((opt) => opt.value === field.value) || null
							}
							isLoading={isLoading}
							isDisabled={disabled}
							isClearable={isClearable}
							isMulti={isMulti}
						/>

						{error && <p className="mt-2 text-red-500 text-sm">{error}</p>}
					</div>
				)}
			/>
		</div>
	);
}

export default ControlledSelectComponent;