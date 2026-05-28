import React from 'react';
import './animations.css'; 

const CarLoading = () => {
  return (
    <div className="flex flex-col items-center justify-center h-64" dir='ltr'>
      <div className="relative flex items-center gap-2.5">

        <div className="">
          <div className="w-3 h-3 bg-gray-500 rounded-full opacity-70 smoke"></div>
       
        </div>

        {/* سيارة تاكسي */}
        <svg
          className="w-28 h-28 text-b bounce-slow"
          viewBox="0 0 640 512"
          fill="currentColor"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M544 192h-16L488.3 84.6A64 64 0 0 0 427.5 48H212.5a64 64 0 0 0-60.8 36.6L112 192H96a96 96 0 0 0-96 96v80a48 48 0 0 0 48 48 64 64 0 0 0 128 0h288a64 64 0 0 0 128 0 48 48 0 0 0 48-48v-80a96 96 0 0 0-96-96zM212.5 96h215a16 16 0 0 1 15.2 10.3L477.3 192H162.7l34.6-85.7A16 16 0 0 1 212.5 96zM144 432a32 32 0 1 1 32-32 32 32 0 0 1-32 32zm352 0a32 32 0 1 1 32-32 32 32 0 0 1-32 32zm96-80a16 16 0 0 1-16 16h-10.7a64 64 0 0 0-122.6 0H197.3a64 64 0 0 0-122.6 0H64a16 16 0 0 1-16-16v-80a64 64 0 0 1 64-64h448a64 64 0 0 1 64 64z" />
        </svg>


      </div>

    </div>
  );
};

export default CarLoading;
