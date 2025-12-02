-- Add caption column to assets table
-- Migration for storing human-readable captions from AssetUpload.caption

-- Add caption column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'assets' AND column_name = 'caption'
    ) THEN
        ALTER TABLE assets ADD COLUMN caption VARCHAR(500) NULL;
        COMMENT ON COLUMN assets.caption IS 'Human-readable caption for HITL preview and alt text. Maps from AssetUpload.caption.';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'assets' AND column_name = 'caption';
