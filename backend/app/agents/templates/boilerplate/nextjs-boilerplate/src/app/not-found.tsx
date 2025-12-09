import Link from 'next/link'
import Image from 'next/image'

export default function NotFound() {
  return (
    <div className="h-screen flex flex-col items-center justify-center bg-white px-4 overflow-hidden">
      <h1 className="text-7xl md:text-8xl font-bold text-gray-800 mb-4">
        404
      </h1>
      
      <div className="mb-4">
        <Image
          src="/image/bg.gif"
          alt="Lost illustration"
          width={550}
          height={350}
          className="object-contain"
          unoptimized
        />
      </div>
      
      <h2 className="text-2xl md:text-3xl font-bold text-gray-800 mb-1">
        Look like you&apos;re lost
      </h2>
      
      <p className="text-gray-500 mb-4">
        the page you are looking for not available!
      </p>
      
      <Link
        href="/"
        className="bg-green-500 hover:bg-green-600 text-white font-medium px-8 py-3 rounded transition-colors"
      >
        Go to Home
      </Link>
    </div>
  )
}
