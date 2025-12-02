-- Storage policies for assets bucket
-- Allows service role to upload/read/delete from inbox/, pending/, and products/ folders

-- Enable RLS on storage.objects if not already enabled
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotent)
DROP POLICY IF EXISTS "Service role full access" ON storage.objects;
DROP POLICY IF EXISTS "Public read access for assets" ON storage.objects;

-- Policy 1: Service role has full access to all storage operations
-- This allows the backend (using service role key) to upload, read, delete
CREATE POLICY "Service role full access"
ON storage.objects
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy 2: Public read access for assets bucket (for public URLs to work)
-- Users can view images via public URLs without authentication
CREATE POLICY "Public read access for assets"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'assets');

-- Verify policies were created
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = 'objects' AND schemaname = 'storage';
