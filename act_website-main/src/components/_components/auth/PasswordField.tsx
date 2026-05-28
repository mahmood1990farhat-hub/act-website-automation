import React from "react";
import { FieldError, UseFormRegister } from "react-hook-form";
import { BsEyeFill, BsEyeSlashFill } from "react-icons/bs";

interface PasswordFieldProps {
  label: string;
  name: string;
  register: UseFormRegister<any>;
  show: boolean;
  setShow: (val: boolean) => void;
  validate?: any;
  error?: FieldError;
}

const PasswordField: React.FC<PasswordFieldProps> = ({
  label,
  name,
  register,
  show,
  setShow,
  validate,
  error,
}) => (
  <div >
    <label className="block mb-1 text-[16px]">{label} <span className=" text-primary">*</span></label>
    <div  className="flex items-center w-full p-2 border-2 bg-foreground border-muted rounded-lg">
      <input
        type={show ? "text" : "password"}
        {...register(name, validate)}
        placeholder="******"
        className="w-full mt-1 focus:outline-none"
      />
      <span className="text-lg cursor-pointer" onClick={() => setShow(!show)}>
        {show ? <BsEyeSlashFill /> : <BsEyeFill />}
      </span>
    </div>
    {error && <p className="text-error text-sm">{error.message}</p>}
  </div>
);

export default PasswordField;
