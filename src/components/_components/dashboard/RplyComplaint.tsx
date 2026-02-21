import { Button } from "@/components/ui/button";
import React from "react";
import { useForm } from "react-hook-form";

type FormData = {
  replyOption: string;
  title: string;
  replyDescription: string;
  resolved?: boolean;
};

export default function RplyComplaint({
  trans,
  closee,
}: {
  trans: any;
  closee: () => void;
}) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      replyOption: "option2",
    },
  });

  const onSubmit = (data: FormData) => {
    console.log("القيمة المرسلة:", data);
  };

  return (
    <div>
      <h1 className="font-bold text-lg mb-4">{trans.complaint.reply.title}</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-2 text-[16px]">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-1 accent-black">
            <input
              type="radio"
              value="option1"
              {...register("replyOption", { required: "اختر أحد الخيارين" })}
              className="w-4 h-4"
            />
            {trans.complaint.reply.withoutReply}
          </label>

          <label className="flex items-center gap-1">
            <input
              type="radio"
              value="option2"
              {...register("replyOption")}
              className="w-4 h-4 accent-black"
            />
            {trans.complaint.reply.sendReply}
          </label>
        </div>
        {errors.replyOption && (
          <p className="text-red-500">{errors.replyOption.message}</p>
        )}

        <div>
          <h1 className="text-start">
            {trans.complaint.reply.replyTitle}{" "}
            <span className="text-primary">*</span>
          </h1>
          <input
            type="text"
            {...register("title", { required: "العنوان مطلوب" })}
            placeholder="title"
            className="p-2 w-full bg-gray-100 rounded-lg border"
          />
          {errors.title && (
            <p className="text-red-500 text-sm">{errors.title.message}</p>
          )}
        </div>

        <div>
          <h1 className="text-start">
            {trans.complaint.reply.replyDescription}{" "}
            <span className="text-primary">*</span>
          </h1>
          <textarea
            rows={4}
            {...register("replyDescription", { required: "الوصف مطلوب" })}
            placeholder="replyDescription"
            className="p-2 w-full bg-gray-100 rounded-lg border"
          />
          {errors.replyDescription && (
            <p className="text-red-500 text-sm">
              {errors.replyDescription.message}
            </p>
          )}
        </div>

        <div className="flex items-center">
          <label className="flex items-center gap-1 accent-primary">
            <input
              type="checkbox"
              className="w-4 h-4"
              {...register("resolved")}
            />
            {trans.complaint.reply.resolvedComplaint}
          </label>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={closee}
            className="flex-1 border border-primary rounded-md p-1 font-bold"
          >
            {trans.complaint.btuBack}
          </button>
          <Button type="submit" className="flex-1">
            {trans.complaint.reply.btuSend}
          </Button>
        </div>
      </form>
    </div>
  );
}
