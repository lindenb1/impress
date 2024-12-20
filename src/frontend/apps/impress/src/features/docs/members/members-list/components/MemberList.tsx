import { Loader } from '@openfun/cunningham-react';
import React, { useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { APIError } from '@/api';
import { Box, Card, InfiniteScroll, TextErrors } from '@/components';
import { useCunninghamTheme } from '@/cunningham';
import { Access, Doc, currentDocRole } from '@/features/docs/doc-management';
import { useResponsiveStore } from '@/stores';

import { useDocAccessesInfinite } from '../api';

import { MemberItem } from './MemberItem';

interface MemberListStateProps {
  isLoading: boolean;
  error: APIError | null;
  accesses?: Access[];
  doc: Doc;
}

const MemberListState = ({
  accesses,
  error,
  isLoading,
  doc,
}: MemberListStateProps) => {
  const { colorsTokens } = useCunninghamTheme();
  const { isSmallMobile } = useResponsiveStore();

  if (error) {
    return <TextErrors causes={error.cause} />;
  }

  if (isLoading || !accesses) {
    return (
      <Box $align="center" className="m-l">
        <Loader />
      </Box>
    );
  }

  return accesses?.map((access, index) => {
    if (!access.user) {
      return null;
    }

    return (
      <Box
        key={`${access.id}-${index}`}
        $background={!(index % 2) ? 'white' : colorsTokens()['greyscale-000']}
        $direction="row"
        $padding={isSmallMobile ? 'tiny' : 'small'}
        $align="center"
        $gap="1rem"
        $radius="4px"
        as="li"
      >
        <MemberItem
          access={access}
          role={access.role}
          doc={doc}
          currentRole={currentDocRole(doc.abilities)}
        />
      </Box>
    );
  });
};

interface MemberListProps {
  doc: Doc;
}

export const MemberList = ({ doc }: MemberListProps) => {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const {
    data,
    isLoading,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useDocAccessesInfinite({
    docId: doc.id,
  });

  const accesses = useMemo(() => {
    return data?.pages.reduce((acc, page) => {
      return acc.concat(page.results);
    }, [] as Access[]);
  }, [data?.pages]);

  return (
    <Card
      $margin="tiny"
      $overflow="auto"
      $maxHeight="80vh"
      $padding="tiny"
      aria-label={t('List members card')}
    >
      <Box ref={containerRef} $overflow="auto">
        <InfiniteScroll
          hasMore={hasNextPage}
          isLoading={isFetchingNextPage}
          next={() => {
            void fetchNextPage();
          }}
          scrollContainer={containerRef.current}
          as="ul"
          $padding="none"
          $margin="none"
          role="listbox"
        >
          <MemberListState
            isLoading={isLoading}
            error={error}
            accesses={accesses}
            doc={doc}
          />
        </InfiniteScroll>
      </Box>
    </Card>
  );
};
