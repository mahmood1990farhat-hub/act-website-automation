import React from "react";
import { FieldError, UseFormRegister } from "react-hook-form";
import { AiOutlineCheck } from "react-icons/ai"; // أيقونة الصح

interface InputFieldProps {
  label: string;
  name: string;
  placeholder: string;
  register: UseFormRegister<any>;
  requiredMsg?: string;
  error?: FieldError;
  type?: string;
  icon?: React.ReactNode;
  value?: string;
}

const InputField: React.FC<InputFieldProps> = ({
  label,
  name,
  icon,
  type = "text",
  placeholder,
  register,
  requiredMsg,
  error,
  value,
}) => {
  const date = new Date().getFullYear();

const prop = type === 'number' ? { max: date, min: 1950 } : {};

  return (
    <div>
      <label className="block mb-1 text-[16px]">
        {label} {requiredMsg && <span className=" text-primary">*</span>}
      </label>

      <div className=" flex items-center w-full min-h-[48px] p-2.5 border-2 bg-foreground border-muted rounded-lg hover:border-primary/50 transition-colors">
        <input
          type={type}
          {...register(name, { 
            required: requiredMsg,
            ...(name === 'home_postcode' ? { minLength: { value: 10, message: 'Must be 10 characters' }, maxLength: { value: 10, message: 'Must be 10 characters' } } : {})
          })}
          placeholder={placeholder}
          className="w-full focus:outline-none bg-foreground"
          {...prop}
        />

        {!error && value && (
          <AiOutlineCheck className="text-green-500 text-xl ml-2" />
        )}
        {icon}
      </div>

      {requiredMsg && error && (
        <p className="text-error text-sm mt-1">{error.message}</p>
      )}
    </div>
  );
};

export default InputField;
