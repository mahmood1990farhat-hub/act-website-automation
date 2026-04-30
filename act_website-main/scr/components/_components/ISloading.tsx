import React from 'react'
import ModernLoading from './loading/ModernLoading'

export default function IsLoadig({ className }: { className?: string }) {
  return (
    <div className={`flex justify-center items-center my-5 ${className || ""}`}>
      <ModernLoading size="md" variant="spinner" />
    </div>
  )
}
