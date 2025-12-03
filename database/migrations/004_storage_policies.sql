-- Storage policies for assets bucket
-- Allows service role AND anon to upload/read/delete from inbox/, pending/, and products/ folders
-- Required because production may use anon key if service role key is not configured

-- Enable RLS on storage.objects if not already enabled
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotent)
DROP POLICY IF EXISTS "Service role full access" ON storage.objects;
DROP POLICY IF EXISTS "Anon full access for assets" ON storage.objects;
DROP POLICY IF EXISTS "Public read access for assets" ON storage.objects;

-- Policy 1: Service role has full access to all storage operations
CREATE POLICY "Service role full access"
ON storage.objects
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy 2: Anon role has full access to assets bucket
-- This allows the backend using anon key to upload/manage files
CREATE POLICY "Anon full access for assets"
ON storage.objects
FOR ALL
TO anon
USING (bucket_id = 'assets')
WITH CHECK (bucket_id = 'assets');

-- Policy 3: Public read access for assets bucket (for public URLs to work)
CREATE POLICY "Public read access for assets"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'assets');

-- Verify policies were created
SELECT schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE tablename = 'objects' AND schemaname = 'storage';
