"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { FaChevronDown, FaChevronUp } from "react-icons/fa";

type AccordionItemProps = {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
};

export function AccordionItem({ title, children, defaultOpen = false }: AccordionItemProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [contentHeight, setContentHeight] = useState<number | undefined>(defaultOpen ? undefined : 0);
  const contentRef = useRef<HTMLDivElement>(null);
  const innerContentRef = useRef<HTMLDivElement>(null);

  // Function to update height - memoized to prevent unnecessary re-renders
  const updateHeight = useCallback(() => {
    if (contentRef.current && isOpen) {
      // Use double requestAnimationFrame to ensure DOM is fully updated
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (contentRef.current) {
            setContentHeight(contentRef.current.scrollHeight);
          }
        });
      });
    }
  }, [isOpen]);

  useEffect(() => {
    if (contentRef.current) {
      if (isOpen) {
        // Use requestAnimationFrame for smooth animation
        updateHeight();
      } else {
        setContentHeight(0);
      }
    }
  }, [isOpen, updateHeight]);

  // Update height when children content changes
  useEffect(() => {
    if (isOpen && contentRef.current) {
      // Immediate update with a small delay to ensure DOM is updated
      const timeoutId = setTimeout(() => {
        updateHeight();
      }, 0);

      // Set up ResizeObserver for continuous monitoring
      const resizeObserver = new ResizeObserver((entries) => {
        // Use requestAnimationFrame to batch updates
        requestAnimationFrame(() => {
          updateHeight();
        });
      });
      
      // Observe both the content container and inner content
      if (contentRef.current) {
        resizeObserver.observe(contentRef.current);
      }
      if (innerContentRef.current) {
        resizeObserver.observe(innerContentRef.current);
      }
      
      return () => {
        clearTimeout(timeoutId);
        resizeObserver.disconnect();
      };
    }
  }, [isOpen, children, updateHeight]);

  // Force update when content might have changed (e.g., after mutations)
  useEffect(() => {
    if (isOpen) {
      // Use MutationObserver to detect DOM changes
      if (innerContentRef.current) {
        const mutationObserver = new MutationObserver(() => {
          updateHeight();
        });
        
        mutationObserver.observe(innerContentRef.current, {
          childList: true,
          subtree: true,
          attributes: false,
          characterData: true,
        });
        
        return () => mutationObserver.disconnect();
      }
    }
  }, [isOpen, updateHeight]);

  // Also update on window resize
  useEffect(() => {
    if (isOpen) {
      const handleResize = () => updateHeight();
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, [isOpen, updateHeight]);

  return (
    <div className="bg-card rounded-xl shadow-xl border-2 border-border overflow-hidden mb-4 transition-all duration-300">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-gradient-to-r from-card to-background px-4 md:px-6 py-3 md:py-4 border-b-2 border-border flex items-center justify-between hover:bg-muted/50 transition-all duration-200"
      >
        <h2 className="text-foreground text-base md:text-xl font-bold flex items-center gap-2">
          <span className="w-1 h-4 md:h-6 bg-primary rounded-full transition-all duration-300"></span>
          <span className="truncate">{title}</span>
        </h2>
        <div className="relative w-5 h-5 flex items-center justify-center flex-shrink-0 ml-2">
          <FaChevronUp className={`text-foreground text-base md:text-lg transition-all duration-300 absolute ${isOpen ? 'rotate-0 opacity-100' : 'rotate-180 opacity-0'}`} />
          <FaChevronDown className={`text-foreground text-base md:text-lg transition-all duration-300 absolute ${isOpen ? 'rotate-180 opacity-0' : 'rotate-0 opacity-100'}`} />
        </div>
      </button>
      <div
        ref={contentRef}
        className="overflow-hidden transition-all duration-500 ease-in-out"
        style={{
          maxHeight: contentHeight !== undefined ? `${contentHeight}px` : isOpen ? 'none' : '0px',
          opacity: isOpen ? 1 : 0,
          transform: isOpen ? 'translateY(0)' : 'translateY(-10px)',
        }}
      >
        <div ref={innerContentRef} className="p-4 md:p-6">
          {children}
        </div>
      </div>
    </div>
  );
}

type PricingAccordionProps = {
  children: React.ReactNode;
};

export default function PricingAccordion({ children }: PricingAccordionProps) {
  return <div className="space-y-4">{children}</div>;
}
