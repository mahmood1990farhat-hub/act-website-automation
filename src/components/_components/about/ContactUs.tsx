import { Button } from '@/components/ui/button';
import React from 'react'

type typeProps={
  form: {
    FullName: string;
    mail: string;
    Yourmessage: string;
    button: string;
}
}
export default function ContactUs({form}:typeProps) {
  return (
     <form
              action=""
              className="flex items-center flex-col gap-4 justify-center py-9 px-16 bg-foreground  rounded-lg shadow-[0_0_15px_rgba(0,0,0,0.25)]"
            >
              <div className="flex  flex-col w-full">
                <label
                  htmlFor="name"
                  className="text-gray-500 text-[14px] mt-1"
                >
                  {form.FullName}
                </label>
                <input
                  type="text"
                  className="px-7 py-2 bg-white w-full border rounded-lg border-muted"
                />
              </div>
              <div className="flex  flex-col w-full">
                <label
                  htmlFor="name"
                  className="text-gray-500 text-[14px] mt-1"
                >
                  {form.mail}
                </label>
                <input
                  type="text"
                  className="px-7 py-2 bg-white w-full border rounded-lg border-muted"
                />
              </div>
              <div className="flex  flex-col w-full">
                <label
                  htmlFor="name"
                  className="text-gray-500 text-[14px] mt-1"
                >
                  {form.Yourmessage}
                </label>
                <textarea
                  rows={5}
                  className="px-7 py-2 bg-white w-full border rounded-lg border-muted"
                />
              </div>
              <Button className="w-full text-lg p-6 cursor-pointer pointer-events-none">
                {form.button}
              </Button>
            </form>
  )
}
