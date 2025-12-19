import { useCallback, useRef, useState } from "react"
import ReactCrop, {
  type Crop,
  centerCrop,
  makeAspectCrop,
} from "react-image-crop"
import "react-image-crop/dist/ReactCrop.css"
import { Loader2, RotateCcw, Upload } from "lucide-react"
import toast from "react-hot-toast"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useUploadAvatar } from "@/queries/profile"

interface AvatarUploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (avatarUrl: string) => void
}

function centerAspectCrop(
  mediaWidth: number,
  mediaHeight: number,
  aspect: number,
) {
  return centerCrop(
    makeAspectCrop(
      {
        unit: "%",
        width: 90,
      },
      aspect,
      mediaWidth,
      mediaHeight,
    ),
    mediaWidth,
    mediaHeight,
  )
}

export function AvatarUploadDialog({
  open,
  onOpenChange,
  onSuccess,
}: AvatarUploadDialogProps) {
  const [imgSrc, setImgSrc] = useState("")
  const [crop, setCrop] = useState<Crop>()
  const [completedCrop, setCompletedCrop] = useState<Crop>()
  const imgRef = useRef<HTMLImageElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadMutation = useUploadAvatar()

  const onSelectFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]

      // Validate file type
      if (!file.type.startsWith("image/")) {
        toast.error("Please select an image file")
        return
      }

      // Validate file size (5MB)
      if (file.size > 5 * 1024 * 1024) {
        toast.error("Image must be less than 5MB")
        return
      }

      const reader = new FileReader()
      reader.addEventListener("load", () => {
        setImgSrc(reader.result?.toString() || "")
      })
      reader.readAsDataURL(file)
    }
  }

  const onImageLoad = useCallback(
    (e: React.SyntheticEvent<HTMLImageElement>) => {
      const { width, height } = e.currentTarget
      setCrop(centerAspectCrop(width, height, 1))
    },
    [],
  )

  const getCroppedImg = useCallback(async (): Promise<Blob | null> => {
    if (!imgRef.current || !completedCrop) return null

    const image = imgRef.current
    const canvas = document.createElement("canvas")
    const ctx = canvas.getContext("2d")
    if (!ctx) return null

    const scaleX = image.naturalWidth / image.width
    const scaleY = image.naturalHeight / image.height

    // Set canvas size to desired output size
    const outputSize = 256
    canvas.width = outputSize
    canvas.height = outputSize

    ctx.drawImage(
      image,
      completedCrop.x * scaleX,
      completedCrop.y * scaleY,
      completedCrop.width * scaleX,
      completedCrop.height * scaleY,
      0,
      0,
      outputSize,
      outputSize,
    )

    return new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.9)
    })
  }, [completedCrop])

  const handleUpload = async () => {
    const croppedBlob = await getCroppedImg()
    if (!croppedBlob) {
      toast.error("Please select and crop an image")
      return
    }

    try {
      const result = await uploadMutation.mutateAsync(croppedBlob)
      toast.success("Avatar updated successfully!")
      onSuccess?.(result.avatar_url)
      handleClose()
    } catch (error: any) {
      toast.error(error.message || "Failed to upload avatar")
    }
  }

  const handleClose = () => {
    setImgSrc("")
    setCrop(undefined)
    setCompletedCrop(undefined)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
    onOpenChange(false)
  }

  const handleReset = () => {
    setImgSrc("")
    setCrop(undefined)
    setCompletedCrop(undefined)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Avatar</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {!imgSrc ? (
            <div
              className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-10 h-10 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                Click to select an image
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                PNG, JPG, GIF up to 5MB
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-center">
                <ReactCrop
                  crop={crop}
                  onChange={(c) => setCrop(c)}
                  onComplete={(c) => setCompletedCrop(c)}
                  aspect={1}
                  circularCrop
                  className="max-h-[300px]"
                >
                  <img
                    ref={imgRef}
                    src={imgSrc}
                    alt="Crop preview"
                    onLoad={onImageLoad}
                    className="max-h-[300px]"
                  />
                </ReactCrop>
              </div>
              <p className="text-xs text-center text-muted-foreground">
                Drag to reposition, resize handles to adjust
              </p>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={onSelectFile}
            className="hidden"
          />
        </div>

        <DialogFooter className="flex gap-2">
          {imgSrc && (
            <Button variant="outline" onClick={handleReset}>
              <RotateCcw className="w-4 h-4 mr-1" />
              Reset
            </Button>
          )}
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!completedCrop || uploadMutation.isPending}
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                Uploading...
              </>
            ) : (
              "Save Avatar"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
