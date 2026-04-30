import React from "react";
import { FieldError, UseFormRegister } from "react-hook-form";
import { AiOutlineCheck } from "react-icons/ai";
import { GrAttachment } from "react-icons/gr";

interface InputFieldProps {
  label: string;
  name: string;
  placeholder: string;
  register: UseFormRegister<any>;
  requiredMsg?: string;
  error?: FieldError;
  value?: FileList;
  multiple?: boolean; // لو حابب تسمح رفع ملفات متعددة
  description?: string; // Description text to help users understand what to upload
}

const FileField: React.FC<InputFieldProps> = ({
  label,
  name,
  value,
  placeholder,
  register,
  requiredMsg,
  error,
  multiple = false,
  description,
}) => {

  const renderFileNames = () => {
    if (!value || value.length === 0) return "Upload";

    if (value.length === 1) return value[0].name;

    return `${value.length} files selected`;
  };

  return (
    <div className="flex flex-col h-full">
      <label className="block mb-2 text-[16px] font-medium">
        {label} {requiredMsg && <span className="text-primary">*</span>}
      </label>
      {description && (
        <p className="text-xs mb-3 leading-relaxed line-clamp-3">
          {description}
        </p>
      )}

      <label 
        dir="rtl"
        htmlFor={name}
        className="flex items-center justify-between w-full min-h-[48px] p-3 border-2 bg-foreground border-muted rounded-lg cursor-pointer hover:border-primary/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <GrAttachment className="text-lg" />
          {!error && value && value.length > 0 && (
            <AiOutlineCheck className="text-green-500 text-xl" />
          )}
        </div>
        <div className="truncate flex-1 text-center px-2">
          {renderFileNames()}
        </div>
        <input
          id={name}
          type="file"
          {...register(name, { required: requiredMsg })}
          placeholder={placeholder}
          className="hidden"
          multiple={multiple}
        />
      </label>

      {requiredMsg && error && (
        <p className="text-error text-sm mt-1">{error.message}</p>
      )}
    </div>
  );
};

export default FileField;
